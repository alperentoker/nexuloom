import math
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from app.core.audit import audit_logger
from app.core.cache import cache
from app.database.registry import connection_registry
from app.database.safety import SQLSafetyValidator


class DataProfiler:
    """Performs deep profiling across tables and columns with chunked processing."""

    def __init__(self, db_name: str, engine: Optional[Engine] = None):
        self.db_name = db_name
        self.engine = engine or connection_registry.get_engine_for(db_name)

    def profile_table(
        self,
        table_name: str,
        sample_size: int = 50000,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Profiles an entire table, analyzing each column according to its data type."""
        safe_table_quoted = SQLSafetyValidator.quote_identifier(table_name)
        cache_key = cache.generate_key("table_profile", self.db_name, table_name, sample_size)
        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                return cached

        # Fetch row count
        total_rows = 0
        try:
            with self.engine.connect() as conn:
                res = conn.execute(text(f'SELECT COUNT(*) FROM {safe_table_quoted}')).scalar()
                total_rows = int(res) if res is not None else 0
        except Exception:
            clean_tbl = SQLSafetyValidator.validate_table_identifier(table_name)
            with self.engine.connect() as conn:
                res = conn.execute(text(f"SELECT COUNT(*) FROM {clean_tbl}")).scalar()
                total_rows = int(res) if res is not None else 0

        # Load sample or full dataset into DataFrame safely
        query = f'SELECT * FROM {safe_table_quoted} LIMIT {sample_size}'
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn)
        except Exception:
            clean_tbl = SQLSafetyValidator.validate_table_identifier(table_name)
            with self.engine.connect() as conn:
                df = pd.read_sql(text(f"SELECT * FROM {clean_tbl} LIMIT {sample_size}"), conn)


        sampled_rows = len(df)
        columns_profile = {}

        for col in df.columns:
            columns_profile[col] = self.profile_column(df[col], col_name=col, total_table_rows=total_rows)

        profile_result = {
            "database_name": self.db_name,
            "table_name": table_name,
            "total_rows": total_rows,
            "sampled_rows": sampled_rows,
            "column_count": len(df.columns),
            "is_sampled": total_rows > sample_size,
            "columns": columns_profile,
        }

        cache.set(cache_key, profile_result, ttl_seconds=3600, database_name=self.db_name, table_name=table_name)
        audit_logger.log(
            action="DATA_PROFILING",
            database_name=self.db_name,
            target=table_name,
            details={"sampled_rows": sampled_rows, "total_rows": total_rows},
        )
        return profile_result

    def profile_column(
        self,
        series: pd.Series,
        col_name: str,
        total_table_rows: int,
    ) -> Dict[str, Any]:
        """Profiles a single Pandas Series."""
        total = len(series)
        null_count = int(series.isna().sum())
        null_pct = round((null_count / total * 100), 2) if total > 0 else 0.0
        non_null_series = series.dropna()
        valid_count = len(non_null_series)
        unique_count = int(non_null_series.nunique())
        duplicate_count = max(0, valid_count - unique_count)

        # Value frequencies (Top 10)
        top_freq = []
        if valid_count > 0:
            vc = non_null_series.value_counts().head(10)
            for val, cnt in vc.items():
                top_freq.append({
                    "value": str(val)[:100],
                    "count": int(cnt),
                    "percentage": round(float(cnt) / valid_count * 100, 2),
                })

        base_profile: Dict[str, Any] = {
            "name": col_name,
            "inferred_type": str(series.dtype),
            "total_count": total,
            "valid_count": valid_count,
            "null_count": null_count,
            "null_percentage": null_pct,
            "unique_count": unique_count,
            "duplicate_count": duplicate_count,
            "most_frequent_values": top_freq,
        }

        # Check if numeric
        if pd.api.types.is_numeric_dtype(series) and not pd.api.types.is_bool_dtype(series):
            num_profile = self._profile_numeric(non_null_series)
            base_profile["type_category"] = "NUMERIC"
            base_profile.update(num_profile)

        # Check if datetime or date string
        elif pd.api.types.is_datetime64_any_dtype(series) or self._is_date_series(series):
            date_profile = self._profile_datetime(series)
            base_profile["type_category"] = "DATETIME"
            base_profile.update(date_profile)

        # String / Categorical / Boolean
        else:
            str_profile = self._profile_string(non_null_series)
            base_profile["type_category"] = "STRING"
            base_profile.update(str_profile)

        return base_profile

    def _profile_numeric(self, s: pd.Series) -> Dict[str, Any]:
        if len(s) == 0:
            return {
                "min": None, "max": None, "mean": None, "median": None,
                "std_dev": None, "skewness": None, "quantiles": {},
                "outliers_count": 0, "distribution_histogram": [],
            }

        s_clean = s[np.isfinite(s)]
        if len(s_clean) == 0:
            return {"min": None, "max": None}

        min_val = float(s_clean.min())
        max_val = float(s_clean.max())
        mean_val = float(s_clean.mean())
        median_val = float(s_clean.median())
        std_val = float(s_clean.std()) if len(s_clean) > 1 else 0.0

        # Quantiles
        q25 = float(s_clean.quantile(0.25))
        q50 = float(s_clean.quantile(0.50))
        q75 = float(s_clean.quantile(0.75))
        q95 = float(s_clean.quantile(0.95))
        iqr = q75 - q25

        # Outliers via IQR
        lower_bound = q25 - 1.5 * iqr
        upper_bound = q75 + 1.5 * iqr
        outliers = s_clean[(s_clean < lower_bound) | (s_clean > upper_bound)]
        outlier_count = int(len(outliers))

        # Skewness
        skewness = float(s_clean.skew()) if len(s_clean) > 2 else 0.0
        if math.isnan(skewness):
            skewness = 0.0

        # Histogram (10 bins)
        hist_counts, bin_edges = np.histogram(s_clean, bins=10)
        hist_data = []
        for i in range(len(hist_counts)):
            hist_data.append({
                "bin_start": round(float(bin_edges[i]), 2),
                "bin_end": round(float(bin_edges[i + 1]), 2),
                "count": int(hist_counts[i]),
            })

        return {
            "min": round(min_val, 4),
            "max": round(max_val, 4),
            "mean": round(mean_val, 4),
            "median": round(median_val, 4),
            "std_dev": round(std_val, 4),
            "skewness": round(skewness, 4),
            "quantiles": {
                "p25": round(q25, 4),
                "p50": round(q50, 4),
                "p75": round(q75, 4),
                "p95": round(q95, 4),
            },
            "iqr": round(iqr, 4),
            "outliers_count": outlier_count,
            "outliers_percentage": round((outlier_count / len(s_clean)) * 100, 2),
            "distribution_histogram": hist_data,
        }

    def _is_date_series(self, s: pd.Series) -> bool:
        sample = s.dropna().head(20)
        if len(sample) == 0:
            return False
        # If column name hints at date
        if any(w in s.name.lower() for w in ("date", "time", "created_at", "updated_at", "timestamp")):
            try:
                pd.to_datetime(sample, errors="raise")
                return True
            except Exception:
                return False
        return False

    def _profile_datetime(self, s: pd.Series) -> Dict[str, Any]:
        dt_s = pd.to_datetime(s, errors="coerce").dropna()
        if len(dt_s) == 0:
            return {"min_date": None, "max_date": None, "frequency": {}}

        min_date = dt_s.min().isoformat()
        max_date = dt_s.max().isoformat()
        span_days = (dt_s.max() - dt_s.min()).days

        # Daily / Weekly / Monthly frequency summary
        monthly_counts = (
            dt_s.dt.to_period("M")
            .value_counts()
            .sort_index()
            .tail(12)
            .to_dict()
        )
        monthly_freq = {str(k): int(v) for k, v in monthly_counts.items()}

        dow_counts = dt_s.dt.day_name().value_counts().to_dict()

        return {
            "min_date": min_date,
            "max_date": max_date,
            "timespan_days": span_days,
            "monthly_distribution": monthly_freq,
            "day_of_week_distribution": {k: int(v) for k, v in dow_counts.items()},
        }

    def _profile_string(self, s: pd.Series) -> Dict[str, Any]:
        str_s = s.astype(str)
        lengths = str_s.str.len()

        empty_strings = int((str_s.str.strip() == "").sum())
        min_len = int(lengths.min()) if len(lengths) > 0 else 0
        max_len = int(lengths.max()) if len(lengths) > 0 else 0
        avg_len = round(float(lengths.mean()), 2) if len(lengths) > 0 else 0.0

        return {
            "min_length": min_len,
            "max_length": max_len,
            "average_length": avg_len,
            "empty_string_count": empty_strings,
        }
