import pytest
from app.metrics.kpi_engine import kpi_engine


def test_kpi_evaluation_and_formula():
    res = kpi_engine.evaluate_kpi("Total Revenue")

    assert res["name"] == "Total Revenue"
    assert res["current_value"] > 0
    assert res["time_series"] is not None
    assert len(res["time_series"]) > 0
    assert res["target_value"] is not None
    assert res["target_achievement_pct"] is not None


def test_average_order_value_kpi():
    res = kpi_engine.evaluate_kpi("Average Order Value")

    assert res["name"] == "Average Order Value"
    assert res["current_value"] > 50.0  # reasonable AOV
    assert res["formula"] == "SUM(total_amount) / COUNT(id)"
