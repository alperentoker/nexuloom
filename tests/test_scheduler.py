import pytest
from app.scheduler.manager import scheduler_engine


def test_scheduler_default_jobs():
    jobs = scheduler_engine.list_jobs()
    assert len(jobs) >= 3
    job_types = [j["job_type"] for j in jobs]
    assert "nightly_scan" in job_types
    assert "monthly_report" in job_types
    assert "drift_snapshot" in job_types


def test_scheduler_toggle_and_crud():
    job = scheduler_engine.add_job(
        name="Test Dynamic Job",
        job_type="nightly_scan",
        schedule_type="interval",
        schedule_value="3600",
        target_db="ALL",
        job_id="test_dynamic_job_1",
    )
    assert job["id"] == "test_dynamic_job_1"
    assert job["is_active"] is True

    # Toggle
    toggled = scheduler_engine.toggle_job("test_dynamic_job_1")
    assert toggled["is_active"] is False

    # Delete
    deleted = scheduler_engine.delete_job("test_dynamic_job_1")
    assert deleted is True
    assert scheduler_engine.get_job("test_dynamic_job_1") is None


def test_scheduler_run_job_now():
    res = scheduler_engine.run_job_now("nightly_quality_scan")
    assert res["status"] in ("SUCCESS", "FAILED")
    assert "started_at" in res
    assert "finished_at" in res

    hist = scheduler_engine.get_history(limit=5)
    assert len(hist) > 0
