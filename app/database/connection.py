import urllib.parse
from typing import Any, Dict, Optional, Tuple
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool, NullPool
import pandas as pd
from app.core.config import settings
from app.core.security import encrypt_secret, decrypt_secret, mask_connection_url
from app.database.safety import SQLSafetyValidator, SQLSafetyError


class DatabaseConnectionManager:
    def __init__(self):
        self._engines: Dict[str, Engine] = {}

    @staticmethod
    def build_connection_url(
        db_type: str,
        database: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> str:
        """Constructs safe, standardized SQLAlchemy connection URL."""
        db_type_lower = db_type.lower().strip()

        if db_type_lower == "sqlite":
            from pathlib import Path
            clean_path = database.strip()
            p = Path(clean_path)
            if not p.exists():
                cand_data = settings.NEXULOOM_DATA_DIR / p.name
                if cand_data.exists():
                    clean_path = str(cand_data)
                else:
                    cand_base = settings.BASE_DIR / "data" / p.name
                    if cand_base.exists():
                        clean_path = str(cand_base)
            return f"sqlite:///{clean_path}"

        # URL encode credentials
        safe_user = urllib.parse.quote_plus(username) if username else ""
        safe_pass = urllib.parse.quote_plus(password) if password else ""
        user_pass = f"{safe_user}:{safe_pass}@" if username else ""
        h = host or "localhost"
        from pathlib import Path
        import os
        in_docker = Path("/.dockerenv").exists() or (os.environ.get("NEXULOOM_ENV") == "development" and Path("/app").exists())

        if db_type_lower in ("postgresql", "postgres"):
            p = port or 5432
            if not in_docker and h in ("postgres-demo", "nexuloom-postgres-demo"):
                h = "localhost"
                p = 5433
            return f"postgresql+psycopg2://{user_pass}{h}:{p}/{database}"
        elif db_type_lower in ("mysql", "mariadb"):
            p = port or 3306
            if not in_docker and h in ("mysql-demo", "nexuloom-mysql-demo"):
                h = "localhost"
                p = 3307
            return f"mysql+pymysql://{user_pass}{h}:{p}/{database}"
        elif db_type_lower in ("mssql", "sqlserver"):
            p = port or 1433
            driver = "ODBC+Driver+18+for+SQL+Server"
            return f"mssql+pyodbc://{user_pass}{h}:{p}/{database}?driver={driver}&TrustServerCertificate=yes"
        else:
            raise ValueError(f"Unsupported database type: {db_type}")

    def get_engine(
        self,
        name: str,
        connection_url: str,
        pool_size: int = 5,
        timeout: int = 30,
    ) -> Engine:
        """Retrieves or creates cached SQLAlchemy engine for the connection."""
        if name in self._engines:
            return self._engines[name]

        is_sqlite = connection_url.startswith("sqlite")
        connect_args = {}
        if is_sqlite:
            # Check same thread false for SQLite
            connect_args = {"check_same_thread": False, "timeout": timeout}
            engine = create_engine(
                connection_url,
                connect_args=connect_args,
                poolclass=NullPool,
                echo=False,
            )
        else:
            engine = create_engine(
                connection_url,
                poolclass=QueuePool,
                pool_size=pool_size,
                max_overflow=10,
                pool_timeout=timeout,
                echo=False,
            )

        self._engines[name] = engine
        return engine

    def test_connection(self, connection_url: str, timeout_seconds: int = 5) -> Tuple[bool, str]:
        """Tests if connection URL can be reached and queried successfully."""
        try:
            is_sqlite = connection_url.startswith("sqlite")
            connect_args = {"timeout": timeout_seconds} if is_sqlite else {}
            engine = create_engine(
                connection_url,
                connect_args=connect_args,
                poolclass=NullPool,
            )
            with engine.connect() as conn:
                # Universal test query
                conn.execute(text("SELECT 1"))
            return True, "Connection successful! Database is online and accessible."
        except Exception as e:
            # Mask any credentials in error message
            msg = mask_connection_url(str(e))
            return False, f"Connection failed: {msg}"

    def execute_read_only_df(
        self,
        engine: Engine,
        sql_query: str,
        params: Optional[Dict[str, Any]] = None,
        max_rows: int = 50000,
        enforce_limit: bool = True,
    ) -> pd.DataFrame:
        """Executes a safe read-only query and returns a Pandas DataFrame."""
        if enforce_limit:
            safe_sql = SQLSafetyValidator.enforce_safety_and_limit(
                sql_query, max_rows=max_rows, default_limit=1000
            )
        else:
            is_valid, err = SQLSafetyValidator.validate_read_only(sql_query)
            if not is_valid:
                raise SQLSafetyError(err)
            safe_sql = sql_query

        with engine.connect() as conn:
            # Set execution options timeout
            conn = conn.execution_options(timeout=settings.UDI_QUERY_TIMEOUT_SECONDS)
            df = pd.read_sql(text(safe_sql), conn, params=params or {})
            return df

    def close_engine(self, name: str) -> None:
        if name in self._engines:
            try:
                self._engines[name].dispose()
            except Exception:
                pass
            del self._engines[name]

    def close_all(self) -> None:
        for name in list(self._engines.keys()):
            self.close_engine(name)


db_manager = DatabaseConnectionManager()
