import pytest
from app.anomaly.detector import AnomalyEngine, AnomalyDetector


def test_anomaly_scanner_production_telemetry():
    engine = AnomalyEngine("demo_enterprise")
    res = engine.scan_table(
        table_name="production",
        metric_col="operating_temp_c",
        method="ALL",
        limit=5000,
    )

    assert res["total_anomalies"] > 0
    assert "CRITICAL" in res["severity_summary"]
    assert res["severity_summary"]["CRITICAL"] > 0

    # Ensure top anomaly is extreme temperature
    top = res["anomalies"][0]
    assert top["observed_value"] >= 90.0
    assert top["severity"] == "CRITICAL"
    assert "Z-SCORE" in top["method"] or "IQR" in top["method"]


def test_severity_mapping():
    assert AnomalyDetector.calculate_severity(4.5) == "CRITICAL"
    assert AnomalyDetector.calculate_severity(3.5) == "HIGH"
    assert AnomalyDetector.calculate_severity(2.8) == "MEDIUM"
    assert AnomalyDetector.calculate_severity(2.1) == "LOW"
