import pytest
from app.rules.rule_engine import business_rule_engine


def test_business_rules_execution():
    res = business_rule_engine.execute_rule("Low Inventory Alert")

    assert res["rule_name"] == "Low Inventory Alert"
    assert res["status"] == "VIOLATION"
    assert res["violation_count"] == 7  # exactly 7 items seeded below min stock
    assert len(res["sample_violations"]) == 7


def test_business_rule_crud():
    rule = business_rule_engine.create_rule(
        name="Test High Defect Rule",
        database_name="demo_enterprise",
        table_name="production",
        condition_sql="defect_rate > 0.04",
        severity="HIGH",
        alert_message="High defects detected!",
    )
    assert rule["name"] == "Test High Defect Rule"

    exec_res = business_rule_engine.execute_rule("Test High Defect Rule")
    assert exec_res["status"] == "VIOLATION"
    assert exec_res["violation_count"] > 0

    # Clean up
    business_rule_engine.delete_rule("Test High Defect Rule")
