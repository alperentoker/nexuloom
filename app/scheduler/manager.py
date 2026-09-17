"""Background Task Scheduler Engine for automated nightly quality scans, monthly dossiers, and drift tracking."""

import os
import json
import sqlite3
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.audit import audit_logger


class SchedulerEngine:
    """Manages APScheduler background tasks, persistence in system.db, and automated triggers."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or settings.SYSTEM_DB_PATH)
        self.scheduler = BackgroundScheduler(daemon=True)
        self._init_db()
        self._seed_default_jobs()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_jobs (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    schedule_type TEXT NOT NULL,
                    schedule_value TEXT NOT NULL,
                    target_db TEXT DEFAULT 'ALL',
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_run_at TEXT,
                    last_status TEXT,
                    last_message TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_job_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    job_name TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    status TEXT NOT NULL,
                    details TEXT,
                    error TEXT
                )
            """)
            conn.commit()

    def _seed_default_jobs(self) -> None:
        defaults = [
            {
                "id": "nightly_quality_scan",
                "name": "Gece 03:00 Otomatik Veri Kalitesi & Anomali Taraması",
                "job_type": "nightly_scan",
                "schedule_type": "cron",
                "schedule_value": "0 3 * * *",
                "target_db": "ALL",
            },
            {
                "id": "monthly_executive_dossier",
                "name": "Ayın 1'i Otomatik PDF/Excel Yönetici Brifingi",
                "job_type": "monthly_report",
                "schedule_type": "cron",
                "schedule_value": "0 6 1 * *",
                "target_db": "ALL",
            },
            {
                "id": "periodic_drift_snapshot",
                "name": "6 Saatlik Şema ve Veri Kayması Snapshot'ı",
                "job_type": "drift_snapshot",
                "schedule_type": "interval",
                "schedule_value": "21600",
                "target_db": "ALL",
            },
        ]

        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            for job in defaults:
                exists = conn.execute("SELECT 1 FROM scheduled_jobs WHERE id = ?", (job["id"],)).fetchone()
                if not exists:
                    conn.execute(
                        """
                        INSERT INTO scheduled_jobs (id, name, job_type, schedule_type, schedule_value, target_db, is_active, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                        """,
                        (job["id"], job["name"], job["job_type"], job["schedule_type"], job["schedule_value"], job["target_db"], now)
                    )
            conn.commit()

    def start(self) -> None:
        """Starts APScheduler and registers all active stored jobs."""
        if not self.scheduler.running:
            self.scheduler.start()

        self._sync_jobs_with_scheduler()

    def shutdown(self) -> None:
        """Gracefully shuts down scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def _sync_jobs_with_scheduler(self) -> None:
        """Loads all active jobs from database and schedules them in APScheduler."""
        jobs = self.list_jobs()
        for job in jobs:
            job_id = job["id"]
            if not job["is_active"]:
                if self.scheduler.get_job(job_id):
                    self.scheduler.remove_job(job_id)
                continue

            # Parse trigger
            trigger = None
            if job["schedule_type"] == "cron":
                parts = job["schedule_value"].split()
                if len(parts) == 5:
                    minute, hour, day, month, day_of_week = parts
                    trigger = CronTrigger(
                        minute=minute, hour=hour, day=day, month=month, day_of_week=day_of_week
                    )
            elif job["schedule_type"] == "interval":
                try:
                    secs = int(job["schedule_value"])
                    trigger = IntervalTrigger(seconds=secs)
                except ValueError:
                    continue

            if trigger:
                if self.scheduler.get_job(job_id):
                    self.scheduler.reschedule_job(job_id, trigger=trigger)
                else:
                    self.scheduler.add_job(
                        func=self._execute_job_handler,
                        args=[job_id],
                        id=job_id,
                        name=job["name"],
                        trigger=trigger,
                        replace_existing=True,
                    )

    def list_jobs(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM scheduled_jobs ORDER BY created_at ASC").fetchall()
            jobs = []
            for r in rows:
                item = dict(r)
                item["is_active"] = bool(item["is_active"])
                # Attach next run time from scheduler
                sched_job = self.scheduler.get_job(item["id"]) if self.scheduler.running else None
                item["next_run_time"] = sched_job.next_run_time.isoformat() if sched_job and sched_job.next_run_time else None
                jobs.append(item)
            return jobs

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM scheduled_jobs WHERE id = ?", (job_id,)).fetchone()
            if not row:
                return None
            item = dict(row)
            item["is_active"] = bool(item["is_active"])
            sched_job = self.scheduler.get_job(job_id) if self.scheduler.running else None
            item["next_run_time"] = sched_job.next_run_time.isoformat() if sched_job and sched_job.next_run_time else None
            return item

    def add_job(
        self,
        name: str,
        job_type: str,
        schedule_type: str,
        schedule_value: str,
        target_db: str = "ALL",
        job_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Adds or updates a scheduled job."""
        jid = job_id or f"job_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scheduled_jobs (id, name, job_type, schedule_type, schedule_value, target_db, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (jid, name, job_type, schedule_type, schedule_value, target_db, now)
            )
            conn.commit()

        self._sync_jobs_with_scheduler()
        return self.get_job(jid)

    def toggle_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        job = self.get_job(job_id)
        if not job:
            return None
        new_state = 0 if job["is_active"] else 1
        with self._get_connection() as conn:
            conn.execute("UPDATE scheduled_jobs SET is_active = ? WHERE id = ?", (new_state, job_id))
            conn.commit()

        self._sync_jobs_with_scheduler()
        return self.get_job(job_id)

    def delete_job(self, job_id: str) -> bool:
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM scheduled_jobs WHERE id = ?", (job_id,))
            conn.commit()
            return cursor.rowcount > 0

    def run_job_now(self, job_id: str) -> Dict[str, Any]:
        """Manually triggers immediate execution of a scheduled job in background."""
        return self._execute_job_handler(job_id)

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM scheduled_job_history ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]

    # Job Executions
    def _execute_job_handler(self, job_id: str) -> Dict[str, Any]:
        job = self.get_job(job_id)
        if not job:
            return {"success": False, "error": f"Job {job_id} not found."}

        started_at = datetime.now(timezone.utc).isoformat()
        job_name = job["name"]
        job_type = job["job_type"]
        target_db = job["target_db"]

        # Insert running history
        hist_id = None
        with self._get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO scheduled_job_history (job_id, job_name, started_at, status)
                VALUES (?, ?, ?, 'RUNNING')
                """,
                (job_id, job_name, started_at)
            )
            hist_id = cur.lastrowid
            conn.commit()

        status = "SUCCESS"
        details_dict = {}
        err_msg = None

        try:
            from app.database.registry import connection_registry
            active_conns = connection_registry.list_connections()
            target_names = [c["name"] for c in active_conns if c.get("is_active")]
            if target_db and target_db != "ALL":
                target_names = [target_db]

            if job_type == "nightly_scan":
                from app.quality.engine import DataQualityEngine
                from app.anomaly.detector import AnomalyEngine
                from app.discovery.schema import SchemaDiscoverer

                scan_results = {}
                total_anomalies = 0
                for db_name in target_names:
                    try:
                        disc = SchemaDiscoverer(db_name)
                        cat = disc.discover_catalog()
                        q_engine = DataQualityEngine(db_name)
                        q_res = q_engine.run_suite(use_cache=False)
                        a_engine = AnomalyEngine(db_name)
                        a_res = a_engine.detect_anomalies(use_cache=False)
                        scan_results[db_name] = {
                            "quality_score": q_res.get("overall_score"),
                            "anomalies_count": len(a_res),
                        }
                        total_anomalies += len(a_res)
                    except Exception as sub_e:
                        scan_results[db_name] = {"error": str(sub_e)}

                details_dict = {
                    "databases_scanned": len(target_names),
                    "total_anomalies": total_anomalies,
                    "details": scan_results,
                }
                msg = f"Nightly scan complete across {len(target_names)} DBs. Found {total_anomalies} anomalies."

            elif job_type == "monthly_report":
                from app.reports.builder import ReportBuilder
                from app.reports.pdf_exporter import PDFExporter
                from app.reports.excel_exporter import ExcelExporter

                reports_dir = settings.BASE_DIR / "reports" / "scheduled"
                reports_dir.mkdir(parents=True, exist_ok=True)

                generated_files = []
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                for db_name in target_names:
                    try:
                        builder = ReportBuilder(db_name)
                        rep_data = builder.build_report_data(
                            title=f"Aylık Yönetim Brifingi - {db_name}",
                            period="Monthly Scheduled Dossier",
                        )
                        pdf_path = reports_dir / f"Dossier_{db_name}_{timestamp_str}.pdf"
                        excel_path = reports_dir / f"Dossier_{db_name}_{timestamp_str}.xlsx"

                        PDFExporter.export(rep_data, pdf_path, language="tr")
                        ExcelExporter.export(rep_data, excel_path, language="tr")

                        generated_files.append(str(pdf_path.name))
                        generated_files.append(str(excel_path.name))
                    except Exception as sub_e:
                        generated_files.append(f"Failed for {db_name}: {str(sub_e)}")

                details_dict = {
                    "output_dir": str(reports_dir),
                    "files_generated": generated_files,
                }
                msg = f"Generated {len(generated_files)} scheduled dossier artifacts."

            elif job_type == "drift_snapshot":
                from app.drift.schema_drift import SchemaDriftTracker
                snapshots_taken = 0
                for db_name in target_names:
                    try:
                        tracker = SchemaDriftTracker(db_name)
                        tracker.take_snapshot()
                        snapshots_taken += 1
                    except Exception as sub_e:
                        pass
                details_dict = {"snapshots_taken": snapshots_taken}
                msg = f"Schema & data drift snapshots recorded for {snapshots_taken} databases."

            else:
                msg = f"Unknown job type '{job_type}' executed."

        except Exception as e:
            status = "FAILED"
            err_msg = str(e)
            msg = f"Execution failed: {err_msg}"
            traceback.print_exc()

        finished_at = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE scheduled_job_history
                SET finished_at = ?, status = ?, details = ?, error = ?
                WHERE id = ?
                """,
                (finished_at, status, json.dumps(details_dict, ensure_ascii=False), err_msg, hist_id)
            )
            conn.execute(
                """
                UPDATE scheduled_jobs
                SET last_run_at = ?, last_status = ?, last_message = ?
                WHERE id = ?
                """,
                (finished_at, status, msg, job_id)
            )
            conn.commit()

        audit_logger.log(
            action="SCHEDULED_JOB_RUN",
            status=status,
            details={"job_id": job_id, "job_name": job_name, "message": msg},
        )

        return {
            "job_id": job_id,
            "status": status,
            "message": msg,
            "started_at": started_at,
            "finished_at": finished_at,
            "details": details_dict,
        }


scheduler_engine = SchedulerEngine()
