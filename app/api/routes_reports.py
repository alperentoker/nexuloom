import os
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from app.core.config import settings
from app.reports.builder import ReportBuilder
from app.reports.html_exporter import HTMLExporter
from app.reports.pdf_exporter import PDFExporter
from app.reports.excel_exporter import ExcelExporter
from app.reports.data_exporter import DataExporter

router = APIRouter(prefix="/api/reports", tags=["Reports"])


class ReportGenerateRequest(BaseModel):
    database_name: str
    title: Optional[str] = None
    period: Optional[str] = None
    sections: Optional[List[str]] = None
    export_format: Optional[str] = "ALL"  # PDF, HTML, EXCEL, CSV, JSON, ALL
    language: Optional[str] = "tr"  # "tr" or "en"


@router.post("/generate")
def generate_report(req: ReportGenerateRequest):
    try:
        builder = ReportBuilder(req.database_name)
        lang = (req.language or "tr").lower()
        data = builder.build_report_data(
            title=req.title,
            period=req.period,
            included_sections=req.sections,
            language=lang,
        )

        fmt = (req.export_format or "ALL").upper()
        generated_files = {}

        if fmt in ("HTML", "ALL"):
            p_html = HTMLExporter.export(data)
            generated_files["HTML"] = p_html.name

        if fmt in ("PDF", "ALL"):
            p_pdf = PDFExporter.export(data)
            generated_files["PDF"] = p_pdf.name

        if fmt in ("EXCEL", "ALL"):
            p_xlsx = ExcelExporter.export(data)
            generated_files["EXCEL"] = p_xlsx.name

        if fmt in ("JSON", "ALL"):
            p_json = DataExporter.export_json(data)
            generated_files["JSON"] = p_json.name

        if fmt in ("CSV", "ALL"):
            p_csv = DataExporter.export_csv(data)
            generated_files["CSV"] = p_csv.name

        return {
            "success": True,
            "report_id": data.get("report_id"),
            "database_name": req.database_name,
            "generated_files": generated_files,
            "report_data": data,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/list")
def list_reports():
    exp_dir = settings.UDI_REPORTS_DIR / "exports"
    files = []
    if exp_dir.exists():
        for f in sorted(exp_dir.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.is_file():
                files.append({
                    "filename": f.name,
                    "size_bytes": f.stat().st_size,
                    "created_at": f.stat().st_mtime,
                    "extension": f.suffix.replace(".", "").upper(),
                })
    return files


@router.get("/download/{filename}")
def download_report(filename: str):
    # Ensure safe path traversal prevention
    safe_name = Path(filename).name
    file_path = settings.UDI_REPORTS_DIR / "exports" / safe_name
    if not file_path.exists():
        sched_path = settings.UDI_REPORTS_DIR / "scheduled" / safe_name
        if sched_path.exists():
            file_path = sched_path
        else:
            raise HTTPException(status_code=404, detail=f"Report file '{filename}' not found.")

    return FileResponse(path=str(file_path), filename=safe_name)


@router.get("/observations/{database_name}")
def get_database_observations(database_name: str, language: str = "tr"):
    try:
        builder = ReportBuilder(database_name)
        lang = (language or "tr").lower()
        data = builder.build_report_data(language=lang)
        return {
            "database_name": database_name,
            "language": lang,
            "observations": data.get("observations", []),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
