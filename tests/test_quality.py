import pytest
from app.quality.engine import DataQualityEngine


def test_table_quality_checks():
    engine = DataQualityEngine("demo_enterprise")
    res = engine.evaluate_table("customers", sample_size=1000)

    assert 0 <= res["quality_score"] <= 100
    assert res["quality_grade"] in ("EXCELLENT", "GOOD", "FAIR", "POOR")
    assert res["total_checks"] > 0

    # Verify NULL check flagged customer email nulls
    null_violations = [v for v in res["violations"] if v["rule_id"] == "QR_NULL_CHECK" and v["column_name"] == "email"]
    assert len(null_violations) > 0, "Expected intentional NULL emails in customers to be detected."


def test_database_quality_summary():
    engine = DataQualityEngine("demo_enterprise")
    res = engine.evaluate_database(sample_size=2000, use_cache=False)

    assert 0 <= res["overall_quality_score"] <= 100
    assert res["tables_analyzed"] >= 10
    assert "scoring_formula" in res
