import pytest
from app.dashboards.manager import custom_dashboard_manager
from app.database.safety import SQLSafetyError


def test_custom_dashboards_crud():
    dashboards = custom_dashboard_manager.list_dashboards()
    assert len(dashboards) >= 1

    d = custom_dashboard_manager.get_dashboard("default_executive_bi")
    assert d is not None
    assert len(d["widgets"]) >= 1


def test_widget_live_execution():
    d = custom_dashboard_manager.get_dashboard("default_executive_bi")
    widgets = d["widgets"]
    kpi_widget = next((w for w in widgets if w["widget_type"] == "kpi_card"), None)
    assert kpi_widget is not None

    data = custom_dashboard_manager.execute_widget_data(kpi_widget)
    assert data["widget_type"] == "kpi_card"
    assert "kpi_value" in data
    assert data["row_count"] >= 1


def test_widget_safety_block():
    with pytest.raises(SQLSafetyError):
        custom_dashboard_manager.add_widget(
            dashboard_id="default_executive_bi",
            title="Malicious Widget",
            widget_type="table",
            database_name="duckdb_analytics",
            sql_query="DROP TABLE sales_analytics",
        )
