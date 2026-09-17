import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from app.core.config import settings
from app.core.i18n import t, localize_kpi_name, localize_severity, localize_rule

_fonts_registered = False


def _ensure_unicode_fonts() -> Tuple[str, str]:
    """Registers Unicode TrueType fonts (DejaVuSans) to ensure Turkish characters render correctly."""
    global _fonts_registered
    if _fonts_registered:
        return "DejaVuSans", "DejaVuSans-Bold"

    regular_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "/usr/local/share/fonts/DejaVuSans.ttf",
    ]
    bold_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "/usr/local/share/fonts/DejaVuSans-Bold.ttf",
    ]

    reg_path = next((p for p in regular_candidates if os.path.exists(p)), None)
    bold_path = next((p for p in bold_candidates if os.path.exists(p)), None)

    if reg_path and bold_path:
        try:
            pdfmetrics.registerFont(TTFont("DejaVuSans", reg_path))
            pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", bold_path))
            pdfmetrics.registerFontFamily("DejaVuSans", normal="DejaVuSans", bold="DejaVuSans-Bold")
            _fonts_registered = True
            return "DejaVuSans", "DejaVuSans-Bold"
        except Exception:
            pass

    return "Helvetica", "Helvetica-Bold"


class PDFExporter:
    """Generates corporate, publication-ready PDF reports using ReportLab with full TR/EN i18n."""

    @classmethod
    def export(
        cls,
        report_data: Dict[str, Any],
        output_path: Optional[Path] = None,
        language: Optional[str] = None,
    ) -> Path:
        lang = language or report_data.get("language", "tr")
        is_tr = lang == "tr"

        reg_font, bold_font = _ensure_unicode_fonts()

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
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Heading1"],
            fontName=bold_font,
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=4,
        )
        meta_style = ParagraphStyle(
            "DocMeta",
            parent=styles["Normal"],
            fontName=reg_font,
            fontSize=8.5,
            leading=11,
            textColor=colors.HexColor("#64748b"),
        )
        section_style = ParagraphStyle(
            "DocSection",
            parent=styles["Heading2"],
            fontName=bold_font,
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=12,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "DocBody",
            parent=styles["Normal"],
            fontName=reg_font,
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#334155"),
        )
        cell_style = ParagraphStyle(
            "DocCell",
            parent=styles["Normal"],
            fontName=reg_font,
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#1e293b"),
        )
        bold_cell_style = ParagraphStyle(
            "DocBoldCell",
            parent=styles["Normal"],
            fontName=bold_font,
            fontSize=8,
            leading=10,
            textColor=colors.HexColor("#0f172a"),
        )

        story = []

        # 1. Header
        title = report_data.get("title") or t("default_report_title", lang)
        period = report_data.get("period") or t("default_period", lang)
        db = report_data.get("database_name", "Database")
        gen_at = report_data.get("generated_at", "")

        story.append(Paragraph(title, title_style))
        meta_line = f"{t('report_period', lang)}: <b>{period}</b> &nbsp;|&nbsp; {t('database', lang)}: <b>{db}</b> &nbsp;|&nbsp; {t('generated_at', lang)}: {gen_at}"
        story.append(Paragraph(meta_line, meta_style))
        story.append(Spacer(1, 8))
        story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=12))

        # 2. Key Executive Observations
        story.append(Paragraph(t("sec_executive_summary", lang), section_style))
        obs = report_data.get("observations", [])
        for i, item in enumerate(obs, start=1):
            bullet_text = f"<b>{i}.</b> {item}"
            story.append(Paragraph(bullet_text, body_style))
            story.append(Spacer(1, 3))
        story.append(Spacer(1, 6))

        # 3. KPI Summary Table
        kpis = report_data.get("kpis", [])
        if kpis:
            story.append(Paragraph(t("kpi_summary_title", lang), section_style))
            kpi_table_data = [
                [
                    Paragraph(t("col_metric", lang), bold_cell_style),
                    Paragraph(t("col_current_value", lang), bold_cell_style),
                    Paragraph(t("col_mom_trend", lang), bold_cell_style),
                    Paragraph(t("col_target", lang), bold_cell_style),
                    Paragraph(t("col_formula", lang), bold_cell_style),
                ]
            ]
            for k in kpis:
                curr = f"{k.get('unit', '')}{k.get('current_value', 0):,}"
                growth = k.get("growth_rate_mom_pct")
                growth_str = f"{growth:+0.1f}%" if growth is not None else "-"
                target = f"{k.get('unit', '')}{k.get('target_value'):,}" if k.get("target_value") else "-"
                k_name = localize_kpi_name(k.get("name", ""), lang)

                kpi_table_data.append([
                    Paragraph(k_name, cell_style),
                    Paragraph(curr, bold_cell_style),
                    Paragraph(growth_str, cell_style),
                    Paragraph(target, cell_style),
                    Paragraph(k.get("formula", ""), cell_style),
                ])

            t_kpi = Table(kpi_table_data, colWidths=[130, 95, 95, 95, 125])
            t_kpi.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]))
            story.append(t_kpi)
            story.append(Spacer(1, 8))

        # 4. Data Quality
        quality = report_data.get("quality", {})
        score = quality.get("overall_quality_score", 100)
        grade = quality.get("overall_grade", "A")
        crit = quality.get("critical_violations", 0)
        tbls = quality.get("tables_analyzed", 0)

        story.append(Paragraph(t("sec_data_quality", lang), section_style))
        if is_tr:
            dq_summary_text = (
                f"Genel Veri Kalitesi Skoru: <b>{score:.0f}/100</b> ({t('quality_grade', lang)}: {grade}). "
                f"Denetlenen Tablo Sayısı: {tbls}; Tespit Edilen Kritik Bütünlük İhlali: {crit}."
            )
        else:
            dq_summary_text = (
                f"Overall Data Quality Score: <b>{score:.0f}/100</b> (Grade: {grade}). "
                f"Analyzed {tbls} database tables; identified {crit} critical integrity concerns."
            )
        story.append(Paragraph(dq_summary_text, body_style))
        story.append(Spacer(1, 6))

        # 5. Statistical Anomalies
        anomalies = report_data.get("anomalies", [])
        if anomalies:
            story.append(Paragraph(t("anom_title", lang), section_style))
            anom_table_data = [
                [
                    Paragraph(t("col_entity", lang), bold_cell_style),
                    Paragraph(t("col_metric", lang), bold_cell_style),
                    Paragraph(t("col_observed", lang), bold_cell_style),
                    Paragraph(t("col_normal_range", lang), bold_cell_style),
                    Paragraph(t("col_deviation", lang), bold_cell_style),
                    Paragraph(t("col_severity", lang), bold_cell_style),
                ]
            ]
            for a in anomalies[:8]:
                sev = localize_severity(a.get("severity", "LOW"), lang)
                anom_table_data.append([
                    Paragraph(str(a.get("entity", "")), cell_style),
                    Paragraph(str(a.get("metric", "")), cell_style),
                    Paragraph(str(a.get("observed_value", "")), bold_cell_style),
                    Paragraph(str(a.get("normal_range", "")), cell_style),
                    Paragraph(str(a.get("deviation_pct", "")), cell_style),
                    Paragraph(sev, bold_cell_style),
                ])

            t_anom = Table(anom_table_data, colWidths=[100, 100, 80, 90, 80, 90])
            t_anom.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ]))
            story.append(t_anom)
            story.append(Spacer(1, 8))

        # 6. Business Rules
        rules = report_data.get("rule_violations", [])
        if rules:
            story.append(Paragraph(t("rules_title", lang), section_style))
            rule_table_data = [
                [
                    Paragraph(t("col_rule_name", lang), bold_cell_style),
                    Paragraph(t("col_target_table", lang), bold_cell_style),
                    Paragraph(t("col_severity", lang), bold_cell_style),
                    Paragraph(t("col_condition", lang), bold_cell_style),
                    Paragraph(t("col_violations", lang), bold_cell_style),
                ]
            ]
            for r in rules:
                loc_r = localize_rule(r.get("rule_name", ""), r.get("alert_message", ""), lang)
                sev = localize_severity(r.get("severity", "HIGH"), lang)
                rule_table_data.append([
                    Paragraph(loc_r["name"], cell_style),
                    Paragraph(str(r.get("table_name", "")), cell_style),
                    Paragraph(sev, bold_cell_style),
                    Paragraph(str(r.get("condition", "")), cell_style),
                    Paragraph(str(r.get("violation_count", 0)), cell_style),
                ])

            t_rule = Table(rule_table_data, colWidths=[130, 95, 75, 140, 100])
            t_rule.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fee2e2")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#fca5a5")),
            ]))
            story.append(t_rule)
            story.append(Spacer(1, 8))

        # 7. Insights
        insights = report_data.get("insights", [])
        if insights:
            story.append(Paragraph(t("insights_title", lang), section_style))
            for ins in insights:
                headline = ins.get("headline_tr") if is_tr and ins.get("headline_tr") else ins.get("headline", "")
                story.append(Paragraph(f"• <b>{headline}</b>", bold_cell_style))
                for f in ins.get("contributing_factors", []):
                    st = f.get("statement_tr") if is_tr and f.get("statement_tr") else f.get("statement", "")
                    story.append(Paragraph(f"&nbsp;&nbsp;&nbsp;&nbsp;→ {st}", body_style))
                story.append(Spacer(1, 4))

        # 8. Footer Note
        story.append(Spacer(1, 14))
        story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cbd5e1"), spaceAfter=6))
        story.append(Paragraph(f"{t('footer_note', lang)} &nbsp;|&nbsp; ID: {report_data.get('report_id', '')}", meta_style))

        doc.build(story)
        return dest
