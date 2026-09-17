from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from app.database.registry import connection_registry
from app.database.safety import SQLSafetyValidator


class RootCauseTreeBuilder:
    """Constructs multi-level hierarchical drill-down trees for root-cause analysis."""

    def __init__(self, db_name: str, engine: Optional[Engine] = None):
        self.db_name = db_name
        self.engine = engine or connection_registry.get_engine_for(db_name)

    def build_drill_down_tree(
        self,
        table_name: str,
        metric_col: str,
        date_col: str,
        dimension_hierarchy: List[str],  # e.g. ["region", "product_category", "customer_tier"]
        sample_limit: int = 50000,
    ) -> Dict[str, Any]:
        """Recursively builds an analytical drill-down tree identifying the biggest variance branch at each tier."""
        safe_table_quoted = SQLSafetyValidator.quote_identifier(table_name)
        safe_metric_col = SQLSafetyValidator.validate_identifier(metric_col)
        safe_date_col = SQLSafetyValidator.validate_identifier(date_col)
        if dimension_hierarchy:
            dimension_hierarchy = [SQLSafetyValidator.validate_identifier(d) for d in dimension_hierarchy]

        query = f'SELECT * FROM {safe_table_quoted} LIMIT {sample_limit}'
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn)
        except Exception:
            clean_tbl = SQLSafetyValidator.validate_table_identifier(table_name)
            with self.engine.connect() as conn:
                df = pd.read_sql(text(f"SELECT * FROM {clean_tbl} LIMIT {sample_limit}"), conn)

        if safe_metric_col not in df.columns or safe_date_col not in df.columns:
            raise ValueError(f"Columns '{safe_metric_col}' and '{safe_date_col}' are required.")


        df["_dt"] = pd.to_datetime(df[date_col], errors="coerce")
        clean_df = df.dropna(subset=["_dt", metric_col]).sort_values("_dt")

        if len(clean_df) < 10:
            return {"name": f"{metric_col} (Insufficient data)", "children": []}

        max_dt = clean_df["_dt"].max()
        split_dt = max_dt - pd.Timedelta(days=30)
        if split_dt <= clean_df["_dt"].min():
            split_dt = clean_df["_dt"].quantile(0.5)

        p1_total = float(clean_df[clean_df["_dt"] < split_dt][metric_col].sum())
        p2_total = float(clean_df[clean_df["_dt"] >= split_dt][metric_col].sum())
        root_pct = ((p2_total - p1_total) / abs(p1_total) * 100) if p1_total != 0 else 0.0

        root_node = {
            "name": f"{metric_col}",
            "value": round(p2_total, 2),
            "delta": round(p2_total - p1_total, 2),
            "percentage_change": f"{root_pct:+0.1f}%",
            "level": 0,
            "dimension": "TOTAL",
            "children": [],
        }

        # Filter valid dimensions
        valid_dims = [d for d in dimension_hierarchy if d in clean_df.columns]
        if not valid_dims:
            return root_node

        self._drill_down_level(
            df=clean_df,
            split_dt=split_dt,
            metric_col=metric_col,
            remaining_dims=valid_dims,
            parent_node=root_node,
            current_level=1,
            max_branches_per_level=3,
        )

        return root_node

    def _drill_down_level(
        self,
        df: pd.DataFrame,
        split_dt: pd.Timestamp,
        metric_col: str,
        remaining_dims: List[str],
        parent_node: Dict[str, Any],
        current_level: int,
        max_branches_per_level: int = 3,
    ) -> None:
        if not remaining_dims or len(df) == 0:
            return

        curr_dim = remaining_dims[0]
        next_dims = remaining_dims[1:]

        p1 = df[df["_dt"] < split_dt]
        p2 = df[df["_dt"] >= split_dt]

        grp1 = p1.groupby(curr_dim)[metric_col].sum()
        grp2 = p2.groupby(curr_dim)[metric_col].sum()
        all_keys = set(grp1.index).union(set(grp2.index))

        branches = []
        for k in all_keys:
            v1 = float(grp1.get(k, 0.0))
            v2 = float(grp2.get(k, 0.0))
            delta = v2 - v1
            pct = ((v2 - v1) / abs(v1) * 100) if v1 != 0 else (100.0 if v2 > 0 else 0.0)

            branches.append({
                "name": f"{curr_dim}: {k}",
                "dimension": curr_dim,
                "key": str(k),
                "value": round(v2, 2),
                "delta": round(delta, 2),
                "percentage_change": f"{pct:+0.1f}%",
                "abs_delta": abs(delta),
                "level": current_level,
                "children": [],
            })

        # Rank branches by largest absolute variance impact
        branches.sort(key=lambda x: x["abs_delta"], reverse=True)
        top_branches = branches[:max_branches_per_level]

        for b in top_branches:
            parent_node["children"].append(b)
            # Filter subset for next level
            subset_df = df[df[curr_dim] == b["key"]]
            self._drill_down_level(
                df=subset_df,
                split_dt=split_dt,
                metric_col=metric_col,
                remaining_dims=next_dims,
                parent_node=b,
                current_level=current_level + 1,
                max_branches_per_level=max_branches_per_level,
            )
