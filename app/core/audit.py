import json
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.security import mask_secret, mask_connection_url, mask_dict_secrets


class AuditLogger:
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
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    database_name TEXT,
                    target TEXT,
                    query_text TEXT,
                    execution_time_ms REAL,
                    status TEXT NOT NULL,
                    details_json TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)")
            conn.commit()

    def log(
        self,
        action: str,
        status: str = "SUCCESS",
        username: str = "analyst",
        database_name: Optional[str] = None,
        target: Optional[str] = None,
        query_text: Optional[str] = None,
        execution_time_ms: float = 0.0,
        details: Optional[Dict[str, Any]] = None,
    ) -> int:
        clean_query = mask_connection_url(query_text) if query_text else None
        clean_details = mask_dict_secrets(details) if details else {}
        timestamp = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO audit_logs (
                    timestamp, username, action, database_name, target,
                    query_text, execution_time_ms, status, details_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    timestamp,
                    username,
                    action,
                    database_name,
                    target,
                    clean_query,
                    execution_time_ms,
                    status,
                    json.dumps(clean_details, default=str),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def list_logs(
        self,
        limit: int = 100,
        offset: int = 0,
        action: Optional[str] = None,
        database_name: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []
        if action:
            query += " AND action = ?"
            params.append(action)
        if database_name:
            query += " AND database_name = ?"
            params.append(database_name)
        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            result = []
            for r in rows:
                item = dict(r)
                if item.get("details_json"):
                    try:
                        item["details"] = json.loads(item["details_json"])
                    except Exception:
                        item["details"] = {}
                else:
                    item["details"] = {}
                result.append(item)
            return result

    def count_logs(self) -> int:
        with self._get_connection() as conn:
            row = conn.execute("SELECT COUNT(*) as count FROM audit_logs").fetchone()
            return row["count"] if row else 0


audit_logger = AuditLogger()
