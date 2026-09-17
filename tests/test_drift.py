import pytest
from app.drift.schema_drift import SchemaDriftTracker
from app.drift.data_drift import DataDriftEngine
from app.database.registry import connection_registry


@pytest.fixture(autouse=True)
def setup_dbs():
    connection_registry.auto_discover_local_sqlite()


def test_schema_drift_tracking():
    tracker = SchemaDriftTracker("duckdb_analytics")
    snapshots = tracker.take_snapshot()
    assert len(snapshots) >= 1

    report = tracker.detect_schema_drift()
    assert report["database_name"] == "duckdb_analytics"
    assert report["overall_status"] in ("STABLE", "DRIFT_DETECTED", "CRITICAL_DRIFT")
    assert len(report["tables"]) >= 1


def test_data_drift_tracking():
    engine = DataDriftEngine("duckdb_analytics")
    baseline = engine.save_baseline_snapshot("sales_analytics")
    assert len(baseline) >= 1

    report = engine.detect_data_drift("sales_analytics")
    assert report["database_name"] == "duckdb_analytics"
    assert report["table_name"] == "sales_analytics"
    assert "columns" in report
    assert len(report["columns"]) >= 1
    for c in report["columns"]:
        assert "ks_statistic" in c
        assert "p_value" in c
        assert "drift_detected" in c
