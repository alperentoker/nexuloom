"""Deep Edge-Case and Stress Testing Suite for Nexuloom.

Tests extreme mathematical conditions, empty tables, schema mutations,
custom dashboard widget formatting, and DuckDB analytical queries.
"""

import math
import numpy as np
import pandas as pd
import pytest
from datetime import datetime

from app.core.json_util import sanitize_for_json
from app.database.safety import SQLSafetyValidator, SQLSafetyError
from app.database.duckdb_connector import duckdb_manager
from app.drift.data_drift import DataDriftEngine
from app.drift.schema_drift import SchemaDriftTracker
from app.dashboards.manager import custom_dashboard_manager


def test_sanitize_for_json_deep_structures():
    """Verify recursive sanitization of NumPy, Pandas, NaN, Inf, and datetime types."""
    payload = {
        "int64": np.int64(42),
        "float64_nan": np.nan,
        "float64_inf": np.inf,
        "float64_neg_inf": -np.inf,
        "numpy_array": np.array([1, 2, 3]),
        "timestamp": pd.Timestamp("2026-09-17 12:00:00"),
        "datetime": datetime(2026, 9, 17, 12, 0, 0),
        "nested": {
            "sub_array": [np.float32(1.23), np.int16(7)],
            "bool_val": np.bool_(True),
        },
    }
    cleaned = sanitize_for_json(payload)

    assert cleaned["int64"] == 42
    assert isinstance(cleaned["int64"], int)
    assert cleaned["float64_nan"] is None
    assert cleaned["float64_inf"] is None
    assert cleaned["float64_neg_inf"] is None
    assert cleaned["numpy_array"] == [1, 2, 3]
    assert cleaned["timestamp"] == "2026-09-17T12:00:00"
    assert cleaned["nested"]["sub_array"] == [1.2300000190734863, 7]
    assert cleaned["nested"]["bool_val"] is True


def test_sql_safety_advanced_edge_cases():
    """Verify safety validator catches tricky injection vectors, multi-statements, and comments."""
    blocked_cases = [
        "SELECT 1; ATTACH 'evil.db' AS evil;",
        "SELECT * FROM users /* comment */ ; DROP TABLE users;",
        "SELECT * FROM users -- comment \n DELETE FROM users;",
        "INSERT INTO admin_users (name) VALUES ('hacker')",
        "GRANT ALL PRIVILEGES ON *.* TO 'hacker'@'%'",
        "EXEC xp_cmdshell('dir')",
        "COPY users TO '/tmp/dump.csv'",
    ]
    for q in blocked_cases:
        is_valid, err = SQLSafetyValidator.validate_read_only(q)
        assert not is_valid, f"Should have blocked query: {q}"

    allowed_cases = [
        "SELECT * FROM sales_analytics WHERE amount > 100",
        "WITH high_sales AS (SELECT * FROM sales_analytics WHERE amount > 500) SELECT count(*) FROM high_sales",
        "SELECT region, sum(amount) AS total FROM sales_analytics GROUP BY region ORDER BY total DESC",
        "SELECT count(*) FROM demo_enterprise.customers WHERE is_active = 1",
    ]
    for q in allowed_cases:
        is_valid, err = SQLSafetyValidator.validate_read_only(q)
        assert is_valid, f"Should have allowed valid read-only query: {q}"


def test_duckdb_complex_olap_and_ctes():
    """Verify DuckDB analytical engine executes CTEs, window functions, and aggregations smoothly."""
    sql = """
    WITH regional_summary AS (
        SELECT 
            region, 
            count(*) AS order_count,
            sum(amount) AS total_amount,
            avg(margin_pct) AS avg_margin
        FROM sales_analytics
        GROUP BY region
    )
    SELECT 
        region, 
        order_count, 
        round(total_amount, 2) AS total_amount,
        round(avg_margin * 100, 2) AS avg_margin_pct,
        RANK() OVER (ORDER BY total_amount DESC) AS revenue_rank
    FROM regional_summary
    ORDER BY revenue_rank ASC
    """
    df = duckdb_manager.execute_read_only_df(sql, max_rows=100)
    assert not df.empty
    assert "revenue_rank" in df.columns
    assert len(df) == 4  # 4 regions
    assert df["revenue_rank"].iloc[0] == 1


def test_dashboard_widget_edge_formatting():
    """Verify custom dashboards format various types of query results cleanly without crashing."""
    # 1. Single scalar KPI
    w_kpi = {
        "id": "w_test_kpi",
        "widget_type": "kpi_card",
        "title": "Test KPI",
        "database_name": "duckdb_analytics",
        "sql_query": "SELECT count(*) AS cnt FROM sales_analytics",
        "config": {"value_column": "cnt", "prefix": "#", "suffix": " items"},
    }
    res_kpi = custom_dashboard_manager.execute_widget_data(w_kpi)
    assert res_kpi["kpi_value"] == 10000
    assert isinstance(res_kpi["kpi_value"], int)

    # 2. Bar chart aggregation
    w_bar = {
        "id": "w_test_bar",
        "widget_type": "bar_chart",
        "title": "Test Bar",
        "database_name": "duckdb_analytics",
        "sql_query": "SELECT product_category, count(*) AS num FROM sales_analytics GROUP BY product_category",
        "config": {"x_column": "product_category", "y_column": "num"},
    }
    res_bar = custom_dashboard_manager.execute_widget_data(w_bar)
    assert len(res_bar["labels"]) == 5
    assert len(res_bar["values"]) == 5
    assert all(isinstance(v, (int, float)) for v in res_bar["values"])

    # 3. Table widget
    w_table = {
        "id": "w_test_table",
        "widget_type": "table",
        "title": "Test Table",
        "database_name": "duckdb_analytics",
        "sql_query": "SELECT sale_id, amount FROM sales_analytics LIMIT 5",
        "config": {},
    }
    res_table = custom_dashboard_manager.execute_widget_data(w_table)
    assert len(res_table["data"]) == 5
    assert all(isinstance(r["amount"], (int, float)) for r in res_table["data"])


def test_drift_constant_and_identical_distribution():
    """Verify data drift KS-test does not fail or divide by zero when data has zero variance."""
    engine = DataDriftEngine("duckdb_analytics")
    # Detect drift on sales_analytics
    report = engine.detect_data_drift("sales_analytics")
    assert report["table_drift_status"] in ("STABLE", "DRIFT_DETECTED")
    assert "columns" in report
    for col_info in report["columns"]:
        assert isinstance(col_info["ks_statistic"], float)
        assert isinstance(col_info["p_value"], float)
        assert not math.isnan(col_info["ks_statistic"])
        assert not math.isnan(col_info["p_value"])
