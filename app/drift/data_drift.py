"""Data Distribution Drift Engine for statistical KS-testing, distribution mutation, and shift tracking."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from scipy.stats import ks_2samp

from app.core.config import settings
from app.database.registry import connection_registry
from app.database.connection import db_manager
from app.database.safety import SQLSafetyValidator


class DataDriftEngine:
    """Calculates statistical distribution drift (Kolmogorov-Smirnov 2-sample test, mean/std shift)."""

    def __init__(self, db_name: str, system_db_path: Optional[str] = None):
        self.db_name = db_name
        self.system_db_path = str(system_db_path or settings.SYSTEM_DB_PATH)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.system_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_drift_baselines (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    database_name TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    column_name TEXT NOT NULL,
                    sample_size INTEGER NOT NULL,
                    mean_val REAL,
                    std_val REAL,
                    min_val REAL,
                    max_val REAL,
                    median_val REAL,
                    p25_val REAL,
                    p75_val REAL,
                    distribution_sample TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE (database_name, table_name, column_name)
                )
            """)
            conn.commit()

    def _fetch_table_sample(self, table_name: str, max_rows: int = 5000) -> pd.DataFrame:
        """Safely pulls a data sample from target database table."""
        safe_tbl = SQLSafetyValidator.validate_identifier(table_name)
        sql = f"SELECT * FROM {safe_tbl} LIMIT {max_rows}"

        conn_info = connection_registry.get_connection(self.db_name)
        if conn_info and conn_info.get("db_type") == "duckdb":
            from app.database.duckdb_connector import duckdb_manager
            return duckdb_manager.execute_read_only_df(sql, max_rows=max_rows)
        else:
            engine = connection_registry.get_engine_for(self.db_name)
            return db_manager.execute_read_only_df(engine, sql, max_rows=max_rows)

    def save_baseline_snapshot(self, table_name: str) -> List[Dict[str, Any]]:
        """Samples numerical columns and establishes a reference statistical baseline."""
        df = self._fetch_table_sample(table_name)
        if df.empty:
            return []

        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        now = datetime.now(timezone.utc).isoformat()
        saved = []

        with self._get_connection() as conn:
            for col in num_cols:
                series = df[col].dropna()
                if len(series) < 5:
                    continue

                sample_vals = series.head(1000).tolist()
                mean_v = float(series.mean())
                std_v = float(series.std()) if len(series) > 1 else 0.0
                min_v = float(series.min())
                max_v = float(series.max())
                median_v = float(series.median())
                p25_v = float(series.quantile(0.25))
                p75_v = float(series.quantile(0.75))

                conn.execute(
                    """
                    INSERT OR REPLACE INTO data_drift_baselines (
                        database_name, table_name, column_name, sample_size,
                        mean_val, std_val, min_val, max_val, median_val, p25_val, p75_val,
                        distribution_sample, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        self.db_name,
                        table_name,
                        col,
                        len(series),
                        mean_v,
                        std_v,
                        min_v,
                        max_v,
                        median_v,
                        p25_v,
                        p75_v,
                        json.dumps(sample_vals),
                        now,
                    )
                )
                saved.append({"column": col, "mean": mean_v, "std": std_v})
            conn.commit()

        return saved

    def detect_data_drift(self, table_name: str) -> Dict[str, Any]:
        """Compares current table numerical distributions with saved statistical baseline."""
        df = self._fetch_table_sample(table_name)
        if df.empty:
            return {
                "database_name": self.db_name,
                "table_name": table_name,
                "status": "EMPTY_TABLE",
                "columns": [],
            }

        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        columns_report = []
        drift_count = 0

        with self._get_connection() as conn:
            for col in num_cols:
                series = df[col].dropna()
                if len(series) < 5:
                    continue

                # Fetch baseline
                row = conn.execute(
                    """
                    SELECT * FROM data_drift_baselines
                    WHERE database_name = ? AND table_name = ? AND column_name = ?
                    """,
                    (self.db_name, table_name, col)
                ).fetchone()

                if not row:
                    # Establish baseline now
                    self.save_baseline_snapshot(table_name)
                    row = conn.execute(
                        """
                        SELECT * FROM data_drift_baselines
                        WHERE database_name = ? AND table_name = ? AND column_name = ?
                        """,
                        (self.db_name, table_name, col)
                    ).fetchone()

                curr_mean = float(series.mean())
                curr_std = float(series.std()) if len(series) > 1 else 0.0
                curr_median = float(series.median())

                if not row:
                    continue

                base_mean = float(row["mean_val"])
                base_std = float(row["std_val"])
                base_sample = json.loads(row["distribution_sample"])
                curr_sample = series.head(1000).tolist()

                # Perform 2-sample Kolmogorov-Smirnov test
                try:
                    ks_res = ks_2samp(base_sample, curr_sample)
                    ks_stat = float(ks_res.statistic)
                    p_val = float(ks_res.pvalue)
                except Exception:
                    ks_stat = 0.0
                    p_val = 1.0

                # Mean shift percentage
                denom = abs(base_mean) if abs(base_mean) > 1e-6 else 1.0
                mean_shift_pct = round(((curr_mean - base_mean) / denom) * 100, 2)

                # Std shift percentage
                denom_std = abs(base_std) if abs(base_std) > 1e-6 else 1.0
                std_shift_pct = round(((curr_std - base_std) / denom_std) * 100, 2)

                # Drift condition: p-value < 0.05 AND ks_stat > 0.15 OR mean shift > 20%
                is_drift = bool((p_val < 0.05 and ks_stat > 0.15) or abs(mean_shift_pct) >= 20.0)

                severity = "NONE"
                if is_drift:
                    drift_count += 1
                    if ks_stat > 0.40 or abs(mean_shift_pct) > 50:
                        severity = "CRITICAL"
                    elif ks_stat > 0.25 or abs(mean_shift_pct) > 30:
                        severity = "HIGH"
                    else:
                        severity = "MEDIUM"

                columns_report.append({
                    "column_name": col,
                    "drift_detected": is_drift,
                    "severity": severity,
                    "ks_statistic": round(ks_stat, 4),
                    "p_value": round(p_val, 6),
                    "mean_shift_pct": mean_shift_pct,
                    "std_shift_pct": std_shift_pct,
                    "baseline_mean": round(base_mean, 2),
                    "current_mean": round(curr_mean, 2),
                    "baseline_median": round(float(row["median_val"]), 2),
                    "current_median": round(curr_median, 2),
                    "baseline_date": row["created_at"],
                    "distribution_summary": (
                        f"Dağılım kayması: KS={ks_stat:.3f}, p={p_val:.4f}, Ortalama sapması: %{mean_shift_pct:+.1f}"
                        if is_drift else "Dağılım temel referans ile tutarlı ve kararlı."
                    ),
                })

        return {
            "database_name": self.db_name,
            "table_name": table_name,
            "total_numerical_columns": len(columns_report),
            "drifted_columns_count": drift_count,
            "table_drift_status": "DRIFT_DETECTED" if drift_count > 0 else "STABLE",
            "columns": columns_report,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
