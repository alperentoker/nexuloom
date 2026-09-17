import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.engine import Engine
from app.core.config import settings
from app.core.security import encrypt_secret, decrypt_secret, mask_secret, mask_connection_url
from app.database.connection import db_manager


class ConnectionRegistry:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or settings.SYSTEM_DB_PATH)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS database_connections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    db_type TEXT NOT NULL,
                    host TEXT,
                    port INTEGER,
                    database_name TEXT NOT NULL,
                    username TEXT,
                    encrypted_password TEXT,
                    raw_url TEXT,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_tested_at TEXT,
                    last_test_status TEXT,
                    last_test_message TEXT
                )
            """)
            conn.commit()

    def add_connection(
        self,
        name: str,
        db_type: str,
        database_name: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        raw_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        encrypted_pass = encrypt_secret(password) if password else ""
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO database_connections (
                    name, db_type, host, port, database_name, username,
                    encrypted_password, raw_url, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    name,
                    db_type,
                    host,
                    port,
                    database_name,
                    username,
                    encrypted_pass,
                    raw_url,
                    now,
                ),
            )
            conn.commit()

        # Invalidate any cached engine
        db_manager.close_engine(name)
        return self.get_connection(name, include_secrets=False)

    def get_connection(self, name: str, include_secrets: bool = False) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM database_connections WHERE name = ?", (name,)
            ).fetchone()
            if not row:
                return None

            data = dict(row)
            if include_secrets:
                data["password"] = decrypt_secret(data["encrypted_password"])
            else:
                data["password"] = "********" if data["encrypted_password"] else ""

            data.pop("encrypted_password", None)
            return data

    def list_connections(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT id, name, db_type, host, port, database_name, username, is_active, created_at, last_tested_at, last_test_status, last_test_message FROM database_connections ORDER BY name ASC"
            ).fetchall()
            return [dict(r) for r in rows]

    def delete_connection(self, name: str) -> bool:
        db_manager.close_engine(name)
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM database_connections WHERE name = ?", (name,))
            conn.commit()
            return cursor.rowcount > 0

    def get_connection_url(self, name: str) -> str:
        conn_info = self.get_connection(name, include_secrets=True)
        if not conn_info:
            raise ValueError(f"Database connection '{name}' not found in registry.")

        if conn_info.get("raw_url"):
            return conn_info["raw_url"]

        return db_manager.build_connection_url(
            db_type=conn_info["db_type"],
            database=conn_info["database_name"],
            host=conn_info.get("host"),
            port=conn_info.get("port"),
            username=conn_info.get("username"),
            password=conn_info.get("password"),
        )

    def get_engine_for(self, name: str) -> Engine:
        url = self.get_connection_url(name)
        return db_manager.get_engine(name=name, connection_url=url)

    def test_and_update_status(self, name: str) -> Dict[str, Any]:
        conn_info = self.get_connection(name, include_secrets=True)
        if not conn_info:
            return {"success": False, "message": f"Connection '{name}' not found."}

        url = self.get_connection_url(name)
        success, message = db_manager.test_connection(url)

        now = datetime.now(timezone.utc).isoformat()
        status = "ONLINE" if success else "OFFLINE"

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE database_connections
                SET last_tested_at = ?, last_test_status = ?, last_test_message = ?
                WHERE name = ?
                """,
                (now, status, message, name),
            )
            conn.commit()

        return {"success": success, "status": status, "message": message, "tested_at": now}

    def auto_discover_local_sqlite(self) -> List[Dict[str, Any]]:
        """Scans workspace directories for SQLite database files and auto-registers them."""
        from pathlib import Path
        search_roots = [
            settings.NEXULOOM_DATA_DIR,
            settings.BASE_DIR / "data",
        ]

        # Check sibling derindex project data if running on host
        sibling_derindex = settings.BASE_DIR.parent / "derindex" / "data"
        if sibling_derindex.exists() and sibling_derindex not in search_roots:
            search_roots.append(sibling_derindex)

        # Check external mounted data in Docker container if present
        external_data = Path("/app/external_data")
        if external_data.exists() and external_data not in search_roots:
            search_roots.append(external_data)

        # Check any extra paths specified via env
        extra_paths = os.environ.get("NEXULOOM_EXTRA_DB_PATHS") or os.environ.get("UDI_EXTRA_DB_PATHS")
        if extra_paths:
            for p_str in extra_paths.replace(";", ":").replace(",", ":").split(":"):
                p_path = Path(p_str.strip())
                if p_path.exists() and p_path not in search_roots:
                    search_roots.append(p_path)

        discovered = []
        existing_names = {c["name"] for c in self.list_connections()}
        existing_paths = set()
        for c in self.list_connections():
            try:
                existing_paths.add(str(Path(c["database_name"]).resolve()))
            except Exception:
                pass

        for root in search_roots:
            if not root.exists():
                continue
            for ext in ("*.db", "*.sqlite", "*.sqlite3"):
                for p in root.rglob(ext):
                    if p.name in ("system.db", "cache.db") or ".venv" in str(p) or ".git" in str(p):
                        continue
                    try:
                        resolved_path = str(p.resolve())
                    except Exception:
                        continue

                    if resolved_path in existing_paths:
                        continue

                    # Check if valid SQLite with at least one table
                    try:
                        test_conn = sqlite3.connect(resolved_path)
                        tables = test_conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                        test_conn.close()
                        if not tables:
                            continue
                    except Exception:
                        continue

                    # Generate clean connection name (strip generic container/root prefixes)
                    parent_dir_name = p.parent.parent.name if p.parent.name in ("data", "db") else p.parent.name
                    if parent_dir_name.lower() in ("app", "root", "home", "workspace", "scratch", "tmp", ""):
                        cand_name = p.stem
                    else:
                        cand_name = f"{parent_dir_name}_{p.stem}" if parent_dir_name and parent_dir_name != p.stem else p.stem
                    counter = 1
                    base_cand = cand_name
                    while cand_name in existing_names:
                        cand_name = f"{base_cand}_{counter}"
                        counter += 1

                    self.add_connection(
                        name=cand_name,
                        db_type="sqlite",
                        database_name=resolved_path,
                    )
                    self.test_and_update_status(cand_name)
                    existing_names.add(cand_name)
                    existing_paths.add(resolved_path)
                    discovered.append(self.get_connection(cand_name))

        # Auto-detect active Docker demo RDBMS containers (PostgreSQL & MySQL)
        in_docker = Path("/.dockerenv").exists() or (os.environ.get("NEXULOOM_ENV") == "development" and Path("/app").exists())
        demo_candidates = [
            {
                "name": "postgres_demo",
                "db_type": "postgresql",
                "host": "postgres-demo" if in_docker else "localhost",
                "port": 5432 if in_docker else 5433,
                "database_name": "analytics_db",
                "username": "nexuloom",
                "password": "nexuloom_secret",
            },
            {
                "name": "mysql_demo",
                "db_type": "mysql",
                "host": "mysql-demo" if in_docker else "localhost",
                "port": 3306 if in_docker else 3307,
                "database_name": "enterprise_crm",
                "username": "nexuloom",
                "password": "nexuloom_secret",
            },
        ]
        for cand in demo_candidates:
            if cand["name"] in existing_names:
                continue
            try:
                test_url = db_manager.build_connection_url(
                    db_type=cand["db_type"],
                    database=cand["database_name"],
                    host=cand["host"],
                    port=cand["port"],
                    username=cand["username"],
                    password=cand["password"],
                )
                success, _ = db_manager.test_connection(test_url, timeout=3)
                if success:
                    self.add_connection(**cand)
                    self.test_and_update_status(cand["name"])
                    existing_names.add(cand["name"])
                    discovered.append(self.get_connection(cand["name"]))
            except Exception:
                pass

        return discovered


connection_registry = ConnectionRegistry()
