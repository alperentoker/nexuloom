import hashlib
import json
import sqlite3
import time
from typing import Any, Optional
from app.core.config import settings


class QueryCache:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or settings.SYSTEM_DB_PATH)
        self._memory_cache = {}
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS query_cache (
                    cache_key TEXT PRIMARY KEY,
                    database_name TEXT,
                    table_name TEXT,
                    data_json TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    expires_at REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_db_table ON query_cache(database_name, table_name)")
            conn.commit()

    @staticmethod
    def generate_key(prefix: str, *args: Any, **kwargs: Any) -> str:
        serialized = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]
        return f"{prefix}:{digest}"

    def get(self, cache_key: str) -> Optional[Any]:
        now = time.time()
        # Check in-memory first
        if cache_key in self._memory_cache:
            data, exp = self._memory_cache[cache_key]
            if now < exp:
                return data
            else:
                del self._memory_cache[cache_key]

        # Check SQLite
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT data_json, expires_at FROM query_cache WHERE cache_key = ?",
                (cache_key,),
            ).fetchone()
            if row:
                if now < row["expires_at"]:
                    try:
                        val = json.loads(row["data_json"])
                        self._memory_cache[cache_key] = (val, row["expires_at"])
                        return val
                    except Exception:
                        return None
                else:
                    # Expired, clean up
                    conn.execute("DELETE FROM query_cache WHERE cache_key = ?", (cache_key,))
                    conn.commit()
        return None

    def set(
        self,
        cache_key: str,
        data: Any,
        ttl_seconds: int = 3600,
        database_name: Optional[str] = None,
        table_name: Optional[str] = None,
    ) -> None:
        now = time.time()
        expires_at = now + ttl_seconds
        self._memory_cache[cache_key] = (data, expires_at)

        data_json = json.dumps(data, default=str)
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO query_cache (
                    cache_key, database_name, table_name, data_json, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (cache_key, database_name, table_name, data_json, now, expires_at),
            )
            conn.commit()

    def invalidate(self, database_name: Optional[str] = None, table_name: Optional[str] = None) -> int:
        """Invalidate cache entries for specific database and/or table."""
        # Evict memory cache
        self._memory_cache.clear()

        query = "DELETE FROM query_cache WHERE 1=1"
        params = []
        if database_name:
            query += " AND database_name = ?"
            params.append(database_name)
        if table_name:
            query += " AND table_name = ?"
            params.append(table_name)

        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.rowcount

    def purge_expired(self) -> int:
        now = time.time()
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM query_cache WHERE expires_at <= ?", (now,))
            conn.commit()
            return cursor.rowcount


cache = QueryCache()
