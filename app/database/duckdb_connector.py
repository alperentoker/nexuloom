"""DuckDB Analytical Engine connector for fast in-process OLAP, Parquet, and CSV analysis."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import duckdb
import pandas as pd
from app.core.config import settings
from app.database.safety import SQLSafetyValidator, SQLSafetyError


class DuckDBManager:
    """Manages DuckDB in-process analytics, Parquet/CSV file querying, and virtual tables."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(settings.NEXULOOM_DATA_DIR / "analytics.duckdb")
        self._conn: Optional[duckdb.DuckDBPyConnection] = None
        self._registered_files: set = set()

    def get_connection(self, read_only: bool = True) -> duckdb.DuckDBPyConnection:
        """Returns active DuckDB connection."""
        config = {}
        try:
            from duckdb_engine import __version__ as de_ver
            from sqlalchemy import __version__ as sa_ver
            config["custom_user_agent"] = f"duckdb_engine/{de_ver}(sqlalchemy/{sa_ver})"
        except Exception:
            pass
        return duckdb.connect(database=self.db_path, read_only=read_only, config=config)

    def auto_register_workspace_files(self, data_dir: Optional[Path] = None) -> List[str]:
        """Automatically registers views for all .parquet and .csv files found in data directories."""
        search_dirs = [
            data_dir or settings.NEXULOOM_DATA_DIR,
            settings.BASE_DIR / "data",
        ]
        registered = []
        config = {}
        try:
            from duckdb_engine import __version__ as de_ver
            from sqlalchemy import __version__ as sa_ver
            config["custom_user_agent"] = f"duckdb_engine/{de_ver}(sqlalchemy/{sa_ver})"
        except Exception:
            pass

        conn = duckdb.connect(database=self.db_path, read_only=False, config=config)
        try:
            for s_dir in search_dirs:
                if not s_dir.exists():
                    continue
                # Parquet files
                for p_file in s_dir.glob("*.parquet"):
                    table_name = p_file.stem.replace("-", "_").replace(" ", "_").lower()
                    clean_path = str(p_file.resolve()).replace("'", "''")
                    try:
                        conn.execute(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_parquet('{clean_path}')")
                        self._registered_files.add(str(p_file.resolve()))
                        registered.append(table_name)
                    except Exception:
                        pass

                # CSV files
                for c_file in s_dir.glob("*.csv"):
                    table_name = c_file.stem.replace("-", "_").replace(" ", "_").lower()
                    clean_path = str(c_file.resolve()).replace("'", "''")
                    try:
                        conn.execute(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_csv_auto('{clean_path}')")
                        self._registered_files.add(str(c_file.resolve()))
                        registered.append(table_name)
                    except Exception:
                        pass
        finally:
            conn.close()

        return registered

    def execute_read_only_df(
        self,
        sql_query: str,
        max_rows: int = 50000,
        enforce_limit: bool = True,
    ) -> pd.DataFrame:
        """Safely executes read-only SQL query on DuckDB and returns pandas DataFrame."""
        # Validate query safety
        is_valid, err = SQLSafetyValidator.validate_read_only(sql_query)
        if not is_valid:
            raise SQLSafetyError(err)

        query = sql_query.strip().rstrip(";")
        if enforce_limit and "limit" not in query.lower():
            query = f"{query} LIMIT {max_rows}"

        conn = self.get_connection()
        try:
            try:
                res = conn.execute(query)
            except duckdb.IOException as ioe:
                if "No files found" in str(ioe):
                    conn.close()
                    self.auto_register_workspace_files()
                    conn = self.get_connection()
                    res = conn.execute(query)
                else:
                    raise
            df = res.df()
            if enforce_limit and len(df) > max_rows:
                df = df.iloc[:max_rows]
            return df
        finally:
            conn.close()

    def get_tables(self) -> List[Dict[str, Any]]:
        """Returns list of all tables and views available in DuckDB session."""
        self.auto_register_workspace_files()
        conn = self.get_connection()
        try:
            rows = conn.execute("SHOW TABLES").fetchall()
            tables = []
            for (tbl_name,) in rows:
                try:
                    cnt = conn.execute(f"SELECT count(*) FROM {tbl_name}").fetchone()[0]
                except Exception:
                    cnt = 0
                tables.append({"name": tbl_name, "row_count": cnt, "type": "view_or_table"})
            return tables
        finally:
            conn.close()

    def get_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """Returns list of column definitions for a given DuckDB table/view."""
        conn = self.get_connection()
        try:
            rows = conn.execute(f"DESCRIBE {table_name}").fetchall()
            cols = []
            for col_name, col_type, is_null, key, default, extra in rows:
                cols.append({
                    "name": col_name,
                    "type": col_type,
                    "nullable": is_null == "YES",
                    "primary_key": key == "PRI" or "key" in str(key).lower(),
                })
            return cols
        finally:
            conn.close()

    def test_connection(self, path: Optional[str] = None) -> Tuple[bool, str]:
        """Tests if DuckDB can be initialized and read files."""
        try:
            test_conn = duckdb.connect(database=path or ":memory:")
            test_conn.execute("SELECT 1").fetchall()
            test_conn.close()
            return True, "DuckDB analytical engine online and ready."
        except Exception as e:
            return False, f"DuckDB connection failed: {str(e)}"


duckdb_manager = DuckDBManager()
