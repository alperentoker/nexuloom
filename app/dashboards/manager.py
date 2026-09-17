"""Custom BI Dashboard and Widget Engine with safe SQL execution and layout persistence."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pandas as pd

from app.core.config import settings
from app.core.json_util import sanitize_for_json
from app.database.registry import connection_registry
from app.database.connection import db_manager
from app.database.safety import SQLSafetyValidator, SQLSafetyError


class CustomDashboardManager:
    """Manages custom BI dashboards, user-defined widgets, positions, and live query execution."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or settings.SYSTEM_DB_PATH)
        self._init_db()
        self._seed_default_dashboard()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS custom_dashboards (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS dashboard_widgets (
                    id TEXT PRIMARY KEY,
                    dashboard_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    widget_type TEXT NOT NULL,
                    database_name TEXT NOT NULL,
                    sql_query TEXT NOT NULL,
                    grid_x INTEGER DEFAULT 0,
                    grid_y INTEGER DEFAULT 0,
                    grid_w INTEGER DEFAULT 6,
                    grid_h INTEGER DEFAULT 4,
                    config_json TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (dashboard_id) REFERENCES custom_dashboards(id) ON DELETE CASCADE
                )
            """)
            conn.commit()

    def _seed_default_dashboard(self) -> None:
        with self._get_connection() as conn:
            exists = conn.execute("SELECT 1 FROM custom_dashboards WHERE id = 'default_executive_bi'").fetchone()
            if exists:
                return

            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """
                INSERT INTO custom_dashboards (id, title, description, created_at, updated_at)
                VALUES ('default_executive_bi', 'Kurumsal Performans & DuckDB Analitik Panosu', 'Parquet ve DuckDB kaynaklı dinamik KPI, grafik ve sorgu bileşenleri', ?, ?)
                """,
                (now, now)
            )

            # Default sample widgets on duckdb_analytics (or first available db)
            widgets = [
                {
                    "id": "w_kpi_total_sales",
                    "dashboard_id": "default_executive_bi",
                    "title": "Toplam Satış Geliri",
                    "widget_type": "kpi_card",
                    "database_name": "duckdb_analytics",
                    "sql_query": "SELECT round(sum(amount), 2) AS total_revenue FROM sales_analytics",
                    "grid_x": 0,
                    "grid_y": 0,
                    "grid_w": 4,
                    "grid_h": 2,
                    "config_json": json.dumps({"value_column": "total_revenue", "prefix": "$", "suffix": ""}),
                    "created_at": now,
                },
                {
                    "id": "w_kpi_avg_margin",
                    "dashboard_id": "default_executive_bi",
                    "title": "Ortalama Kar Marjı",
                    "widget_type": "kpi_card",
                    "database_name": "duckdb_analytics",
                    "sql_query": "SELECT round(avg(margin_pct) * 100, 1) AS avg_margin FROM sales_analytics",
                    "grid_x": 4,
                    "grid_y": 0,
                    "grid_w": 4,
                    "grid_h": 2,
                    "config_json": json.dumps({"value_column": "avg_margin", "prefix": "%", "suffix": ""}),
                    "created_at": now,
                },
                {
                    "id": "w_kpi_total_orders",
                    "dashboard_id": "default_executive_bi",
                    "title": "İşlenen Sipariş Adedi",
                    "widget_type": "kpi_card",
                    "database_name": "duckdb_analytics",
                    "sql_query": "SELECT count(*) AS total_orders FROM sales_analytics",
                    "grid_x": 8,
                    "grid_y": 0,
                    "grid_w": 4,
                    "grid_h": 2,
                    "config_json": json.dumps({"value_column": "total_orders", "prefix": "", "suffix": " sipariş"}),
                    "created_at": now,
                },
                {
                    "id": "w_bar_category_revenue",
                    "dashboard_id": "default_executive_bi",
                    "title": "Kategori Bazlı Ciro Dağılımı",
                    "widget_type": "bar_chart",
                    "database_name": "duckdb_analytics",
                    "sql_query": "SELECT product_category, round(sum(amount), 2) AS revenue FROM sales_analytics GROUP BY product_category ORDER BY revenue DESC",
                    "grid_x": 0,
                    "grid_y": 2,
                    "grid_w": 6,
                    "grid_h": 4,
                    "config_json": json.dumps({"x_column": "product_category", "y_column": "revenue", "color": "#06b6d4"}),
                    "created_at": now,
                },
                {
                    "id": "w_donut_region_split",
                    "dashboard_id": "default_executive_bi",
                    "title": "Bölgesel Satış Oranları",
                    "widget_type": "donut_chart",
                    "database_name": "duckdb_analytics",
                    "sql_query": "SELECT region, count(*) AS order_count FROM sales_analytics GROUP BY region ORDER BY order_count DESC",
                    "grid_x": 6,
                    "grid_y": 2,
                    "grid_w": 6,
                    "grid_h": 4,
                    "config_json": json.dumps({"label_column": "region", "value_column": "order_count"}),
                    "created_at": now,
                },
                {
                    "id": "w_table_top_transactions",
                    "dashboard_id": "default_executive_bi",
                    "title": "En Yüksek Tutarlı İşlemler (Top 10)",
                    "widget_type": "table",
                    "database_name": "duckdb_analytics",
                    "sql_query": "SELECT sale_id, customer_segment, product_category, amount, region, sale_date FROM sales_analytics ORDER BY amount DESC LIMIT 10",
                    "grid_x": 0,
                    "grid_y": 6,
                    "grid_w": 12,
                    "grid_h": 4,
                    "config_json": json.dumps({}),
                    "created_at": now,
                },
            ]

            for w in widgets:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO dashboard_widgets (
                        id, dashboard_id, title, widget_type, database_name, sql_query,
                        grid_x, grid_y, grid_w, grid_h, config_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        w["id"], w["dashboard_id"], w["title"], w["widget_type"], w["database_name"],
                        w["sql_query"], w["grid_x"], w["grid_y"], w["grid_w"], w["grid_h"],
                        w["config_json"], w["created_at"],
                    )
                )
            conn.commit()

    def list_dashboards(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM custom_dashboards ORDER BY created_at ASC").fetchall()
            dashboards = []
            for r in rows:
                item = dict(r)
                w_count = conn.execute(
                    "SELECT count(*) FROM dashboard_widgets WHERE dashboard_id = ?", (item["id"],)
                ).fetchone()[0]
                item["widget_count"] = w_count
                dashboards.append(item)
            return dashboards

    def get_dashboard(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM custom_dashboards WHERE id = ?", (dashboard_id,)).fetchone()
            if not row:
                return None
            data = dict(row)
            w_rows = conn.execute(
                "SELECT * FROM dashboard_widgets WHERE dashboard_id = ? ORDER BY grid_y ASC, grid_x ASC",
                (dashboard_id,)
            ).fetchall()
            widgets = []
            for wr in w_rows:
                wd = dict(wr)
                wd["config"] = json.loads(wd["config_json"]) if wd["config_json"] else {}
                widgets.append(wd)
            data["widgets"] = widgets
            return data

    def create_dashboard(self, title: str, description: Optional[str] = None) -> Dict[str, Any]:
        d_id = f"dash_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO custom_dashboards (id, title, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (d_id, title, description or "", now, now)
            )
            conn.commit()
        return self.get_dashboard(d_id)

    def update_dashboard(self, dashboard_id: str, title: str, description: Optional[str] = None) -> Optional[Dict[str, Any]]:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE custom_dashboards SET title = ?, description = ?, updated_at = ? WHERE id = ?",
                (title, description or "", now, dashboard_id)
            )
            conn.commit()
        return self.get_dashboard(dashboard_id)

    def delete_dashboard(self, dashboard_id: str) -> bool:
        with self._get_connection() as conn:
            conn.execute("DELETE FROM dashboard_widgets WHERE dashboard_id = ?", (dashboard_id,))
            cur = conn.execute("DELETE FROM custom_dashboards WHERE id = ?", (dashboard_id,))
            conn.commit()
            return cur.rowcount > 0

    def add_widget(
        self,
        dashboard_id: str,
        title: str,
        widget_type: str,
        database_name: str,
        sql_query: str,
        grid_w: int = 6,
        grid_h: int = 4,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        # Validate query safety
        is_valid, err = SQLSafetyValidator.validate_read_only(sql_query)
        if not is_valid:
            raise SQLSafetyError(err)

        w_id = f"w_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        now = datetime.now(timezone.utc).isoformat()

        # Find position for new widget
        with self._get_connection() as conn:
            max_y_row = conn.execute(
                "SELECT max(grid_y + grid_h) FROM dashboard_widgets WHERE dashboard_id = ?", (dashboard_id,)
            ).fetchone()
            grid_y = max_y_row[0] if max_y_row and max_y_row[0] is not None else 0

            cfg_json = json.dumps(config or {})
            conn.execute(
                """
                INSERT INTO dashboard_widgets (
                    id, dashboard_id, title, widget_type, database_name, sql_query,
                    grid_x, grid_y, grid_w, grid_h, config_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)
                """,
                (w_id, dashboard_id, title, widget_type, database_name, sql_query, grid_y, grid_w, grid_h, cfg_json, now)
            )
            conn.commit()

        return self.get_widget(w_id)

    def get_widget(self, widget_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM dashboard_widgets WHERE id = ?", (widget_id,)).fetchone()
            if not row:
                return None
            wd = dict(row)
            wd["config"] = json.loads(wd["config_json"]) if wd["config_json"] else {}
            return wd

    def update_widget(
        self,
        widget_id: str,
        title: Optional[str] = None,
        widget_type: Optional[str] = None,
        database_name: Optional[str] = None,
        sql_query: Optional[str] = None,
        grid_x: Optional[int] = None,
        grid_y: Optional[int] = None,
        grid_w: Optional[int] = None,
        grid_h: Optional[int] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        current = self.get_widget(widget_id)
        if not current:
            return None

        if sql_query:
            is_valid, err = SQLSafetyValidator.validate_read_only(sql_query)
            if not is_valid:
                raise SQLSafetyError(err)

        new_title = title if title is not None else current["title"]
        new_type = widget_type if widget_type is not None else current["widget_type"]
        new_db = database_name if database_name is not None else current["database_name"]
        new_sql = sql_query if sql_query is not None else current["sql_query"]
        new_gx = grid_x if grid_x is not None else current["grid_x"]
        new_gy = grid_y if grid_y is not None else current["grid_y"]
        new_gw = grid_w if grid_w is not None else current["grid_w"]
        new_gh = grid_h if grid_h is not None else current["grid_h"]
        new_cfg = json.dumps(config if config is not None else current["config"])

        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE dashboard_widgets
                SET title = ?, widget_type = ?, database_name = ?, sql_query = ?,
                    grid_x = ?, grid_y = ?, grid_w = ?, grid_h = ?, config_json = ?
                WHERE id = ?
                """,
                (new_title, new_type, new_db, new_sql, new_gx, new_gy, new_gw, new_gh, new_cfg, widget_id)
            )
            conn.commit()

        return self.get_widget(widget_id)

    def delete_widget(self, widget_id: str) -> bool:
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM dashboard_widgets WHERE id = ?", (widget_id,))
            conn.commit()
            return cur.rowcount > 0

    def execute_widget_data(self, widget: Dict[str, Any]) -> Dict[str, Any]:
        """Safely executes the widget SQL query and shapes data according to widget_type."""
        db_name = widget["database_name"]
        sql = widget["sql_query"]
        w_type = widget["widget_type"]
        cfg = widget.get("config", {})

        # Safety check
        is_valid, err = SQLSafetyValidator.validate_read_only(sql)
        if not is_valid:
            raise SQLSafetyError(err)

        conn_info = connection_registry.get_connection(db_name)
        if not conn_info:
            raise ValueError(f"Database connection '{db_name}' not found.")

        if conn_info.get("db_type") == "duckdb":
            from app.database.duckdb_connector import duckdb_manager
            df = duckdb_manager.execute_read_only_df(sql, max_rows=5000)
        else:
            engine = connection_registry.get_engine_for(db_name)
            df = db_manager.execute_read_only_df(engine, sql, max_rows=5000)

        columns = list(df.columns)
        records = df.to_dict(orient="records")

        # Format by widget type
        formatted: Dict[str, Any] = {
            "widget_id": widget.get("id"),
            "widget_type": w_type,
            "title": widget.get("title"),
            "database_name": db_name,
            "row_count": len(records),
            "columns": columns,
        }

        if w_type == "kpi_card":
            val_col = cfg.get("value_column") or (columns[0] if columns else None)
            val = df[val_col].iloc[0] if (val_col and not df.empty) else 0
            formatted["kpi_value"] = val
            formatted["prefix"] = cfg.get("prefix", "")
            formatted["suffix"] = cfg.get("suffix", "")

        elif w_type in ("bar_chart", "line_chart"):
            x_col = cfg.get("x_column") or (columns[0] if len(columns) > 0 else "")
            y_col = cfg.get("y_column") or (columns[1] if len(columns) > 1 else (columns[0] if columns else ""))
            labels = df[x_col].astype(str).tolist() if x_col in df.columns else []
            values = df[y_col].fillna(0).tolist() if y_col in df.columns else []
            formatted["labels"] = labels
            formatted["values"] = values
            formatted["x_label"] = x_col
            formatted["y_label"] = y_col
            formatted["color"] = cfg.get("color", "#06b6d4")

        elif w_type == "donut_chart":
            lbl_col = cfg.get("label_column") or (columns[0] if len(columns) > 0 else "")
            val_col = cfg.get("value_column") or (columns[1] if len(columns) > 1 else (columns[0] if columns else ""))
            labels = df[lbl_col].astype(str).tolist() if lbl_col in df.columns else []
            values = df[val_col].fillna(0).tolist() if val_col in df.columns else []
            formatted["labels"] = labels
            formatted["values"] = values

        else:  # table or custom
            formatted["data"] = records[:100]

        return sanitize_for_json(formatted)


custom_dashboard_manager = CustomDashboardManager()
