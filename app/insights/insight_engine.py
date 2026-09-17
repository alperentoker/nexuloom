from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from app.core.lineage import lineage_tracker
from app.database.registry import connection_registry


class InsightEngine:
    """Discovers multi-dimensional contributing factors and correlational attribution for metric changes."""

    def __init__(self, db_name: str, engine: Optional[Engine] = None):
        self.db_name = db_name
        self.engine = engine or connection_registry.get_engine_for(db_name)

    def analyze_metric_variance(
        self,
        table_name: str,
        metric_col: str,
        date_col: str,
        dimension_cols: Optional[List[str]] = None,
        period_split_date: Optional[str] = None,
        sample_limit: int = 50000,
    ) -> Dict[str, Any]:
        """Decomposes the variance of a metric between two consecutive periods across categorical dimensions."""
        query = f'SELECT * FROM "{table_name}" LIMIT {sample_limit}'
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn)
        except Exception:
            with self.engine.connect() as conn:
                df = pd.read_sql(text(f"SELECT * FROM {table_name} LIMIT {sample_limit}"), conn)

        if metric_col not in df.columns or date_col not in df.columns:
            raise ValueError(f"Required columns '{metric_col}' or '{date_col}' not found in '{table_name}'.")

        df["_dt"] = pd.to_datetime(df[date_col], errors="coerce")
        clean_df = df.dropna(subset=["_dt", metric_col]).sort_values("_dt")

        if len(clean_df) < 10:
            return {
                "status": "INSUFFICIENT_DATA",
                "message": "Not enough chronological data points to perform variance attribution.",
                "insights": [],
            }

        # Determine split date (midpoint or user-specified)
        if period_split_date:
            split_dt = pd.to_datetime(period_split_date)
        else:
            # Last 30 days vs prior 30 days, or median date
            max_dt = clean_df["_dt"].max()
            split_dt = max_dt - pd.Timedelta(days=30)
            if split_dt <= clean_df["_dt"].min():
                # Fallback to median date
                split_dt = clean_df["_dt"].quantile(0.5)

        p1 = clean_df[clean_df["_dt"] < split_dt]
        p2 = clean_df[clean_df["_dt"] >= split_dt]

        if len(p1) == 0 or len(p2) == 0:
            return {"status": "INSUFFICIENT_PERIODS", "message": "Cannot partition data into two time periods.", "insights": []}

        p1_val = float(p1[metric_col].sum())
        p2_val = float(p2[metric_col].sum())
        total_delta = p2_val - p1_val
        pct_change = ((p2_val - p1_val) / abs(p1_val) * 100) if p1_val != 0 else 0.0

        direction_verb = "increased" if total_delta > 0 else "decreased"
        headline = f"{metric_col} {direction_verb} {abs(pct_change):.1f}% in the current period (from {p1_val:,.1f} to {p2_val:,.1f})."

        # Determine dimensions to analyze
        if not dimension_cols:
            # Auto-detect low-to-medium cardinality categorical columns
            candidates = []
            for col in df.columns:
                if col not in (metric_col, date_col, "_dt") and 2 <= df[col].nunique() <= 50:
                    candidates.append(col)
            dimension_cols = candidates[:3]

        contributing_factors = []
        dimension_breakdowns = {}

        for dim in (dimension_cols or []):
            if dim not in df.columns:
                continue

            grp1 = p1.groupby(dim)[metric_col].sum()
            grp2 = p2.groupby(dim)[metric_col].sum()
            all_keys = set(grp1.index).union(set(grp2.index))

            items = []
            for k in all_keys:
                v1 = float(grp1.get(k, 0.0))
                v2 = float(grp2.get(k, 0.0))
                d = v2 - v1
                c_pct = ((v2 - v1) / abs(v1) * 100) if v1 != 0 else (100.0 if v2 > 0 else 0.0)
                # Share of total variance
                share_of_total_delta = (d / total_delta * 100) if total_delta != 0 else 0.0

                items.append({
                    "dimension_value": str(k),
                    "prior_value": round(v1, 2),
                    "current_value": round(v2, 2),
                    "delta": round(d, 2),
                    "percentage_change": round(c_pct, 2),
                    "share_of_variance": round(share_of_total_delta, 2),
                })

            # Sort items by negative contribution if decline, or positive contribution if increase
            items.sort(key=lambda x: x["delta"] if total_delta < 0 else -x["delta"])
            dimension_breakdowns[dim] = items

            # Identify top driver
            if items:
                top_driver = items[0]
                if abs(top_driver["share_of_variance"]) > 15.0:
                    verb = "accounted for" if top_driver["share_of_variance"] > 0 else "counterbalanced"
                    attribution_factor = (
                        f"Dimension '{dim}' ({top_driver['dimension_value']}) is a significant contributor: "
                        f"{verb} {abs(top_driver['share_of_variance']):.1f}% of the observed net variance "
                        f"(changed from {top_driver['prior_value']:,.1f} to {top_driver['current_value']:,.1f}, {top_driver['percentage_change']:+0.1f}%)."
                    )
                    contributing_factors.append({
                        "dimension": dim,
                        "key": top_driver["dimension_value"],
                        "share_of_variance_pct": top_driver["share_of_variance"],
                        "statement": attribution_factor,
                    })

        # Record lineage
        insight_id = f"INSIGHT:{table_name}_{metric_col}_{split_dt.date()}"
        lineage_tracker.record(
            item_type="INSIGHT",
            item_id=insight_id,
            item_label=headline,
            source_db=self.db_name,
            source_table=table_name,
            source_query=query,
            metadata={"pct_change": pct_change, "contributing_factors_count": len(contributing_factors)},
        )

        return {
            "database_name": self.db_name,
            "table_name": table_name,
            "metric": metric_col,
            "insight_id": insight_id,
            "headline": headline,
            "direction": direction_verb,
            "percentage_change": round(pct_change, 2),
            "prior_period_total": round(p1_val, 2),
            "current_period_total": round(p2_val, 2),
            "period_split_timestamp": split_dt.isoformat(),
            "contributing_factors": contributing_factors,
            "dimension_breakdowns": dimension_breakdowns,
            "causality_disclaimer": "Contributing factors denote correlational variance attribution; they do not imply sole direct causality.",
        }
