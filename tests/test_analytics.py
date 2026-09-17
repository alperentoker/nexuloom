import pytest
from app.analytics.trends import TrendAnalyzer


def test_trend_analysis_upward():
    # Upward trajectory
    series = [
        {"period": "2026-01", "value": 100.0},
        {"period": "2026-02", "value": 108.0},
        {"period": "2026-03", "value": 121.0},
        {"period": "2026-04", "value": 117.0},
        {"period": "2026-05", "value": 139.0},
    ]

    res = TrendAnalyzer.analyze_series(series, metric_name="Revenue", unit="₺")

    assert res["trend_direction"] == "UPWARD"
    assert res["total_growth_percentage"] == 39.0
    assert res["linear_slope"] > 0
    assert res["r_squared"] > 0.75
    assert "increased 39.0%" in res["explanation"]
    assert len(res["moving_average_series"]) == 5


def test_trend_analysis_sudden_change():
    # Stable then sudden drop
    series = [
        {"period": "2026-01", "value": 500.0},
        {"period": "2026-02", "value": 502.0},
        {"period": "2026-03", "value": 498.0},
        {"period": "2026-04", "value": 501.0},
        {"period": "2026-05", "value": 180.0},  # sudden crash
    ]

    res = TrendAnalyzer.analyze_series(series, metric_name="Output")
    assert len(res["sudden_changes"]) > 0
    assert res["sudden_changes"][0]["to_period"] == "2026-05"
