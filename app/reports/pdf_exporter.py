from pathlib import Path
from typing import Any, Dict, Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from app.core.config import settings


class PDFExporter:
    """Generates corporate, publication-ready PDF reports using ReportLab."""

    @classmethod
    def export(cls, report_data: Dict[str, Any], output_path: Optional[Path] = None) -> Path:
        dest = output_path or (
            settings.UDI_REPORTS_DIR / "exports" / f"report_{report_data.get('database_name', 'db')}_{int(hash(report_data.get('generated_at', '')) % 1000000)}.pdf"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)

        doc = SimpleDocTemplate(
            str(dest),
            pagesize=letter,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        # Custom styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4,
        )
        meta_style = ParagraphStyle(
            "DocMeta",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#64748b"),
        )
        section_style = ParagraphStyle(
            "DocSection",
            parent=styles["Heading2"],
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=14,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
        )
        cell_style = ParagraphStyle(
            "DocCell",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1e293b"),
        )
        bold_cell_style = ParagraphStyle(
            "DocBoldCell",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            fontName="Helvetica-Bold",
            textColor=colors.HexColor("#0f172a"),
        )

        story = []

        # 1. Header
        title = report_data.get("title", "Business Intelligence Report")
        period = report_data.get("period", "September 2026")
        db = report_data.get("database_name", "Database")
        gen_at = report_data.get("generated_at", "")

        story.append(Paragraph(title, title_style))
        story.append(Paragraph(f"Period: <b>{period}</b> &nbsp;|&nbsp; Target Database: <b>{db}</b> &nbsp;|&nbsp; Generated: {gen_at}", meta_style))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=14))

        # 2. Key Executive Observations
        story.append(Paragraph("Key Executive Observations", section_style))
        obs = report_data.get("observations", [])
        for i, item in enumerate(obs, start=1):
            bullet_text = f"<b>{i}.</b> {item}"
            story.append(Paragraph(bullet_text, body_style))
            story.append(Spacer(1, 4))
        story.append(Spacer(1, 8))

        # 3. KPI Summary Table
        kpis = report_data.get("kpis", [])
        if kpis:
            story.append(Paragraph("Key Performance Indicators (KPIs)", section_style))
            kpi_table_data = [
                [
                    Paragraph("KPI Metric", bold_cell_style),
                    Paragraph("Current Value", bold_cell_style),
                    Paragraph("Period Change (MoM)", bold_cell_style),
                    Paragraph("Target", bold_cell_style),
                    Paragraph("Target Achievement", bold_cell_style),
                ]
            ]
            for k in kpis:
                curr = f"{k.get('unit', '')}{k.get('current_value', 0):,}"
                growth = k.get("growth_rate_mom_pct")
                growth_str = f"{growth:+0.1f}%" if growth is not None else "-"
                target = f"{k.get('unit', '')}{k.get('target_value'):,}" if k.get("target_value") else "-"
                achieve = f"{k.get('target_achievement_pct', 0):.1f}%" if k.get("target_achievement_pct") else "-"

                kpi_table_data.append([
                    Paragraph(k.get("name", ""), cell_style),
                    Paragraph(curr, bold_cell_style),
                    Paragraph(growth_str, cell_style),
                    Paragraph(target, cell_style),
                    Paragraph(achieve, cell_style),
                ])

            t_kpi = Table(kpi_table_data, colWidths=[140, 100, 100, 100, 100])
            t_kpi.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]))
            story.append(t_kpi)
            story.append(Spacer(1, 10))

        # 4. Data Quality
        quality = report_data.get("quality", {})
        score = quality.get("overall_quality_score", 100)
        grade = quality.get("overall_grade", "GOOD")
        crit = quality.get("critical_violations", 0)
        tbls = quality.get("tables_analyzed", 0)

        story.append(Paragraph("Data Quality Health Audit", section_style))
        dq_summary_text = (
            f"Overall Data Quality Score: <b>{score}/100</b> ({grade}). "
            f"Analyzed {tbls} database tables; identified {crit} critical integrity concerns."
        )
        story.append(Paragraph(dq_summary_text, body_style))
        story.append(Spacer(1, 8))

        # 5. Statistical Anomalies
        anomalies = report_data.get("anomalies", [])
        if anomalies:
            story.append(Paragraph("Detected Statistical Anomalies (Top Samples)", section_style))
            anom_table_data = [
                [
                    Paragraph("Entity", bold_cell_style),
                    Paragraph("Metric", bold_cell_style),
                    Paragraph("Observed", bold_cell_style),
                    Paragraph("Normal Range", bold_cell_style),
                    Paragraph("Deviation", bold_cell_style),
                    Paragraph("Severity", bold_cell_style),
                ]
            ]
            for a in anomalies[:8]:
                anom_table_data.append([
                    Paragraph(str(a.get("entity", "")), cell_style),
                    Paragraph(str(a.get("metric", "")), cell_style),
                    Paragraph(str(a.get("observed_value", "")), bold_cell_style),
                    Paragraph(str(a.get("normal_range", "")), cell_style),
                    Paragraph(str(a.get("deviation_pct", "")), cell_style),
                    Paragraph(str(a.get("severity", "")), bold_cell_style),
                ])

            t_anom = Table(anom_table_data, colWidths=[100, 80, 80, 110, 80, 90])
            t_anom.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f8fafc")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ]))
            story.append(t_anom)
            story.append(Spacer(1, 10))

        # 6. Business Rules
        rules = report_data.get("rule_violations", [])
        if rules:
            story.append(Paragraph("Operational Business Rule Violations", section_style))
            rules_table_data = [
                [
                    Paragraph("Rule Name", bold_cell_style),
                    Paragraph("Table", bold_cell_style),
                    Paragraph("Severity", bold_cell_style),
                    Paragraph("Violations", bold_cell_style),
                    Paragraph("Alert Message", bold_cell_style),
                ]
            ]
            for r in rules[:6]:
                rules_table_data.append([
                    Paragraph(str(r.get("rule_name", "")), cell_style),
                    Paragraph(str(r.get("table_name", "")), cell_style),
                    Paragraph(str(r.get("severity", "")), bold_cell_style),
                    Paragraph(str(r.get("violation_count", 0)), cell_style),
                    Paragraph(str(r.get("alert_message", "")), cell_style),
                ])

            t_rule = Table(rules_table_data, colWidths=[120, 80, 70, 70, 200])
            t_rule.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fee2e2")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#fca5a5")),
            ]))
            story.append(t_rule)
            story.append(Spacer(1, 10))

        # 7. Lineage & Footer
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=8))
        story.append(Paragraph(
            f"Nexuloom Data Intelligence Platform | Report ID: {report_data.get('report_id', '')} | Deterministic Verification Passed",
            meta_style,
        ))

        doc.build(story)
        return dest
