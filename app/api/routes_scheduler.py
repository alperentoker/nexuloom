"""FastAPI routes for Scheduled Tasks and Background Automation."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.scheduler.manager import scheduler_engine

router = APIRouter(prefix="/api/scheduler", tags=["Scheduler Automation"])


class CreateJobRequest(BaseModel):
    name: str = Field(..., description="Human-readable job name")
    job_type: str = Field(..., description="Job handler type: nightly_scan, monthly_report, or drift_snapshot")
    schedule_type: str = Field("cron", description="cron or interval")
    schedule_value: str = Field(..., description="Cron expression (e.g. '0 3 * * *') or interval in seconds")
    target_db: Optional[str] = Field("ALL", description="Database target name or ALL")


@router.get("/jobs")
def get_scheduled_jobs():
    """Lists all configured background automation jobs and their execution states."""
    return {"jobs": scheduler_engine.list_jobs()}


@router.post("/jobs")
def create_scheduled_job(req: CreateJobRequest):
    """Creates or updates a scheduled background automation job."""
    if req.schedule_type not in ("cron", "interval"):
        raise HTTPException(status_code=400, detail="schedule_type must be either 'cron' or 'interval'.")

    if req.job_type not in ("nightly_scan", "monthly_report", "drift_snapshot"):
        raise HTTPException(status_code=400, detail="Invalid job_type. Allowed: nightly_scan, monthly_report, drift_snapshot.")

    job = scheduler_engine.add_job(
        name=req.name,
        job_type=req.job_type,
        schedule_type=req.schedule_type,
        schedule_value=req.schedule_value,
        target_db=req.target_db or "ALL",
    )
    return {"success": True, "job": job}


@router.post("/jobs/{job_id}/run")
def run_job_manually(job_id: str):
    """Triggers immediate on-demand execution of a scheduled job."""
    job = scheduler_engine.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")

    res = scheduler_engine.run_job_now(job_id)
    return res


@router.post("/jobs/{job_id}/toggle")
def toggle_job_active(job_id: str):
    """Pauses or resumes a scheduled background automation job."""
    job = scheduler_engine.toggle_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return {"success": True, "job": job}


@router.delete("/jobs/{job_id}")
def delete_scheduled_job(job_id: str):
    """Deletes a scheduled job from the engine."""
    success = scheduler_engine.delete_job(job_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return {"success": True, "message": f"Job '{job_id}' removed successfully."}


@router.get("/history")
def get_scheduler_history(limit: int = 50):
    """Returns the historical execution audit logs for scheduled jobs."""
    return {"history": scheduler_engine.get_history(limit=limit)}
