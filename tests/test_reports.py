import pytest
import openpyxl
from pathlib import Path
from app.reports.builder import ReportBuilder
from app.reports.html_exporter import HTMLExporter
from app.reports.pdf_exporter import PDFExporter
from app.reports.excel_exporter import ExcelExporter
from app.reports.data_exporter import DataExporter


def test_full_report_generation():
    builder = ReportBuilder("demo_enterprise")
    data = builder.build_report_data(title="Integration Test Report", period="Q3 2026")

    assert data["database_name"] == "demo_enterprise"
    assert len(data["kpis"]) > 0
    assert len(data["observations"]) > 0

    # 1. HTML Export
    html_file = HTMLExporter.export(data)
    assert html_file.exists()
    assert html_file.stat().st_size > 1000
    with open(html_file, "r", encoding="utf-8") as f:
        html_txt = f.read()
    assert "Integration Test Report" in html_txt
    assert "Key Performance Indicators" in html_txt

    # 2. PDF Export
    pdf_file = PDFExporter.export(data)
    assert pdf_file.exists()
    assert pdf_file.stat().st_size > 1000

    # 3. Excel Export with 6 Worksheets
    xlsx_file = ExcelExporter.export(data)
    assert xlsx_file.exists()
    wb = openpyxl.load_workbook(xlsx_file)
    expected_sheets = ["Summary", "KPIs", "Trends", "Anomalies", "Data Quality", "Raw Results"]
    for s in expected_sheets:
        assert s in wb.sheetnames

    # 4. JSON & CSV
    json_file = DataExporter.export_json(data)
    assert json_file.exists()
    csv_file = DataExporter.export_csv(data)
    assert csv_file.exists()
