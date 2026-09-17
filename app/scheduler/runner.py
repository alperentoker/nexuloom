import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.audit import audit_logger
from app.reports.builder import ReportBuilder
from app.reports.html_exporter import HTMLExporter
from app.reports.pdf_exporter import PDFExporter
from app.reports.excel_exporter import ExcelExporter


class ReportScheduler:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or settings.SYSTEM_DB_PATH)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    database_name TEXT NOT NULL,
                    frequency TEXT NOT NULL,
                    report_format TEXT NOT NULL DEFAULT 'ALL',
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_run_at TEXT,
                    last_status TEXT,
                    last_output_path TEXT
                )
            """)
            conn.commit()

    def create_schedule(
        self,
        name: str,
        database_name: str,
        frequency: str = "WEEKLY",  # "DAILY", "WEEKLY", "MONTHLY"
        report_format: str = "ALL",  # "PDF", "HTML", "EXCEL", "ALL"
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO scheduled_reports (
                    name, database_name, frequency, report_format, is_active, created_at
                ) VALUES (?, ?, ?, ?, 1, ?)
                """,
                (name, database_name, frequency.upper(), report_format.upper(), now),
            )
            conn.commit()
        return self.get_schedule(name)

    def get_schedule(self, name: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM scheduled_reports WHERE name = ?", (name,)).fetchone()
            return dict(row) if row else None

    def list_schedules(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM scheduled_reports ORDER BY id DESC").fetchall()
            return [dict(r) for r in rows]

    def delete_schedule(self, name: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM scheduled_reports WHERE name = ?", (name,))
            conn.commit()
            return cursor.rowcount > 0

    def trigger_job(self, name: str) -> Dict[str, Any]:
        """Executes a scheduled job immediately and writes files to reports/scheduled/."""
        job = self.get_schedule(name)
        if not job:
            raise ValueError(f"Schedule '{name}' not found.")

        db_name = job["database_name"]
        fmt = job.get("report_format", "ALL").upper()
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        title = f"{job['frequency'].capitalize()} Automated Report - {name}"

        builder = ReportBuilder(db_name)
        data = builder.build_report_data(title=title, period=f"{job['frequency']} Batch")

        out_dir = settings.UDI_REPORTS_DIR / "scheduled"
        out_dir.mkdir(parents=True, exist_ok=True)
        generated_files = []

        try:
            if fmt in ("HTML", "ALL"):
                p_html = out_dir / f"{name}_{timestamp_str}.html"
                HTMLExporter.export(data, output_path=p_html)
                generated_files.append(str(p_html))

            if fmt in ("PDF", "ALL"):
                p_pdf = out_dir / f"{name}_{timestamp_str}.pdf"
                PDFExporter.export(data, output_path=p_pdf)
                generated_files.append(str(p_pdf))

            if fmt in ("EXCEL", "ALL"):
                p_xlsx = out_dir / f"{name}_{timestamp_str}.xlsx"
                ExcelExporter.export(data, output_path=p_xlsx)
                generated_files.append(str(p_xlsx))

            now_iso = datetime.now(timezone.utc).isoformat()
            status = "SUCCESS"
            last_out = ", ".join(generated_files)

            with self._get_connection() as conn:
                conn.execute(
                    """
                    UPDATE scheduled_reports
                    SET last_run_at = ?, last_status = ?, last_output_path = ?
                    WHERE name = ?
                    """,
                    (now_iso, status, last_out, name),
                )
                conn.commit()

            audit_logger.log(
                action="SCHEDULED_REPORT_RUN",
                status="SUCCESS",
                database_name=db_name,
                target=name,
                details={"files": generated_files},
            )

            return {"success": True, "files": generated_files, "run_at": now_iso}

        except Exception as e:
            now_iso = datetime.now(timezone.utc).isoformat()
            with self._get_connection() as conn:
                conn.execute(
                    "UPDATE scheduled_reports SET last_run_at = ?, last_status = ? WHERE name = ?",
                    (now_iso, f"FAILED: {str(e)}", name),
                )
                conn.commit()
            return {"success": False, "error": str(e)}


report_scheduler = ReportScheduler()
