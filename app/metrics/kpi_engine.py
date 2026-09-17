import sqlite3
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from app.core.config import settings
from app.core.lineage import lineage_tracker
from app.database.registry import connection_registry
from app.database.safety import SQLSafetyValidator, SQLSafetyError


class KPIEngine:
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
                CREATE TABLE IF NOT EXISTS kpi_definitions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    database_name TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    formula TEXT NOT NULL,
                    date_column TEXT,
                    target_value REAL,
                    unit TEXT DEFAULT '',
                    higher_is_better INTEGER DEFAULT 1,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL
                )
            """)
            conn.commit()

    def add_kpi(
        self,
        name: str,
        database_name: str,
        table_name: str,
        formula: str,
        description: str = "",
        date_column: Optional[str] = None,
        target_value: Optional[float] = None,
        unit: str = "",
        higher_is_better: bool = True,
    ) -> Dict[str, Any]:
        # Validate table name and date column
        safe_table = SQLSafetyValidator.validate_table_identifier(table_name)
        safe_date_col = SQLSafetyValidator.validate_identifier(date_column) if date_column else None

        # Validate formula against whitelist and injection patterns
        is_safe_formula, err, _ = SQLSafetyValidator.validate_kpi_formula(formula)
        if not is_safe_formula:
            raise SQLSafetyError(f"Invalid KPI formula: {err}")

        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO kpi_definitions (
                    name, description, database_name, table_name, formula,
                    date_column, target_value, unit, higher_is_better, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    name,
                    description,
                    database_name,
                    safe_table,
                    formula,
                    safe_date_col,
                    target_value,
                    unit,
                    1 if higher_is_better else 0,
                    now,
                ),
            )
            conn.commit()
        return self.get_kpi(name)

    def get_kpi(self, name: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM kpi_definitions WHERE name = ?", (name,)).fetchone()
            return dict(row) if row else None

    def list_kpis(self, database_name: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM kpi_definitions WHERE is_active = 1"
        params = []
        if database_name:
            query += " AND database_name = ?"
            params.append(database_name)
        query += " ORDER BY name ASC"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def delete_kpi(self, name: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM kpi_definitions WHERE name = ?", (name,))
            conn.commit()
            return cursor.rowcount > 0

    def evaluate_kpi(
        self,
        kpi_name: str,
        engine: Optional[Engine] = None,
    ) -> Dict[str, Any]:
        """Calculates current value, historical periods, and target comparisons."""
        kpi = self.get_kpi(kpi_name)
        if not kpi:
            raise ValueError(f"KPI '{kpi_name}' does not exist.")

        db_name = kpi["database_name"]
        table_name = kpi["table_name"]
        formula = kpi["formula"]
        date_col = kpi["date_column"]
        target = kpi["target_value"]
        eng = engine or connection_registry.get_engine_for(db_name)

        # Validate identifiers and formula
        safe_table_quoted = SQLSafetyValidator.quote_identifier(table_name)
        is_safe_formula, err, formula_cols = SQLSafetyValidator.validate_kpi_formula(formula)
        if not is_safe_formula:
            raise SQLSafetyError(f"Invalid KPI formula: {err}")

        # 1. Total Aggregate
        agg_sql = f'SELECT {formula} AS kpi_val FROM {safe_table_quoted}'
        try:
            with eng.connect() as conn:
                res = conn.execute(text(agg_sql)).scalar()
                current_val = float(res) if res is not None else 0.0
        except Exception:
            clean_tbl = SQLSafetyValidator.validate_table_identifier(table_name)
            with eng.connect() as conn:
                res = conn.execute(text(f"SELECT {formula} AS kpi_val FROM {clean_tbl}")).scalar()
                current_val = float(res) if res is not None else 0.0

        # Lineage record
        lineage_tracker.record(
            item_type="KPI",
            item_id=f"KPI:{kpi_name}",
            item_label=f"KPI: {kpi_name} = {current_val} {kpi.get('unit', '')}",
            source_db=db_name,
            source_table=table_name,
            source_query=agg_sql,
            metadata={"formula": formula, "current_value": current_val},
        )

        time_series = []
        prev_period_val = None
        prev_year_val = None
        growth_rate_mom = None
        growth_rate_yoy = None

        # 2. Time-based slicing if date_column exists
        if date_col:
            safe_date_col = SQLSafetyValidator.validate_identifier(date_col)
            # Memory optimization: project ONLY required columns rather than SELECT *
            # Include date column and columns extracted from formula
            cols_needed = [safe_date_col]
            for fc in formula_cols:
                if fc != "*":
                    cols_needed.append(SQLSafetyValidator.validate_identifier(fc))
            unique_cols = list(dict.fromkeys(cols_needed))
            cols_clause = ", ".join(f'"{c}"' for c in unique_cols)

            ts_query = (
                f'SELECT {cols_clause} FROM {safe_table_quoted} '
                f'WHERE "{safe_date_col}" IS NOT NULL '
                f'ORDER BY "{safe_date_col}" DESC LIMIT 50000'
            )
            try:
                with eng.connect() as conn:
                    raw_df = pd.read_sql(text(ts_query), conn)
            except Exception:
                # Fallback query with safe identifiers
                with eng.connect() as conn:
                    raw_df = pd.read_sql(text(f'SELECT * FROM {safe_table_quoted} LIMIT 50000'), conn)


            if date_col in raw_df.columns and len(raw_df) > 0:
                raw_df["_dt"] = pd.to_datetime(raw_df[date_col], errors="coerce")
                valid_df = raw_df.dropna(subset=["_dt"]).sort_values("_dt")
                if len(valid_df) > 0:
                    valid_df["_month"] = valid_df["_dt"].dt.to_period("M").astype(str)
                    
                    # Calculate formula per month
                    monthly_groups = []
                    for m, grp in valid_df.groupby("_month"):
                        val = self._evaluate_formula_on_df(formula, grp)
                        monthly_groups.append({"period": m, "value": round(val, 2)})

                    time_series = monthly_groups

                    if len(monthly_groups) >= 2:
                        curr_m = monthly_groups[-1]["value"]
                        prev_m = monthly_groups[-2]["value"]
                        prev_period_val = prev_m
                        if prev_m != 0:
                            growth_rate_mom = round(((curr_m - prev_m) / abs(prev_m)) * 100, 2)

                    if len(monthly_groups) >= 13:
                        prev_y = monthly_groups[-13]["value"]
                        prev_year_val = prev_y
                        if prev_y != 0:
                            growth_rate_yoy = round(((monthly_groups[-1]["value"] - prev_y) / abs(prev_y)) * 100, 2)

        # Target comparison
        target_diff = None
        target_achievement_pct = None
        if target is not None and target != 0:
            target_diff = round(current_val - target, 2)
            target_achievement_pct = round((current_val / target) * 100, 2)

        return {
            "name": kpi_name,
            "description": kpi.get("description"),
            "formula": formula,
            "database_name": db_name,
            "table_name": table_name,
            "current_value": round(current_val, 2),
            "unit": kpi.get("unit", ""),
            "target_value": target,
            "target_diff": target_diff,
            "target_achievement_pct": target_achievement_pct,
            "previous_period_value": prev_period_val,
            "growth_rate_mom_pct": growth_rate_mom,
            "growth_rate_yoy_pct": growth_rate_yoy,
            "time_series": time_series,
        }

    def _evaluate_formula_on_df(self, formula: str, df: pd.DataFrame) -> float:
        """Evaluates simple aggregation formulas on a dataframe deterministically."""
        clean = formula.strip().upper()
        # Handle SUM(col) / COUNT(col)
        division_match = re.match(r"^SUM\((.*?)\)\s*\/\s*COUNT\((.*?)\)$", clean)
        if division_match:
            col1 = division_match.group(1).strip().lower()
            col2 = division_match.group(2).strip().lower()
            c1_match = [c for c in df.columns if c.lower() == col1]
            c2_match = [c for c in df.columns if c.lower() == col2]
            s = df[c1_match[0]].sum() if c1_match else 0.0
            cnt = df[c2_match[0]].count() if c2_match else len(df)
            return float(s / cnt) if cnt > 0 else 0.0

        # Handle SUM(col)
        sum_match = re.match(r"^SUM\((.*?)\)$", clean)
        if sum_match:
            col = sum_match.group(1).strip().lower()
            c_match = [c for c in df.columns if c.lower() == col]
            return float(df[c_match[0]].sum()) if c_match else 0.0

        # Handle COUNT(col) or COUNT(*)
        count_match = re.match(r"^COUNT\((.*?)\)$", clean)
        if count_match:
            col = count_match.group(1).strip().lower()
            if col == "*":
                return float(len(df))
            c_match = [c for c in df.columns if c.lower() == col]
            return float(df[c_match[0]].count()) if c_match else float(len(df))

        # Handle AVG(col)
        avg_match = re.match(r"^AVG\((.*?)\)$", clean)
        if avg_match:
            col = avg_match.group(1).strip().lower()
            c_match = [c for c in df.columns if c.lower() == col]
            return float(df[c_match[0]].mean()) if c_match else 0.0

        return 0.0


kpi_engine = KPIEngine()
