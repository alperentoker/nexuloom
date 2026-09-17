from pathlib import Path
from typing import Any, Dict, Optional
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from app.core.config import settings
from app.core.i18n import t, localize_kpi_name, localize_severity, localize_trend_direction, localize_rule


class ExcelExporter:
    """Generates multi-worksheet corporate Excel report using openpyxl with full TR/EN i18n."""

    HEADER_FILL = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
    HEADER_FONT = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    TITLE_FONT = Font(name="Calibri", size=14, bold=True, color="0F172A")
    BOLD_FONT = Font(name="Calibri", size=11, bold=True)
    REGULAR_FONT = Font(name="Calibri", size=11)
    THIN_BORDER = Border(
        left=Side(style="thin", color="E2E8F0"),
        right=Side(style="thin", color="E2E8F0"),
        top=Side(style="thin", color="E2E8F0"),
        bottom=Side(style="thin", color="E2E8F0"),
    )

    @classmethod
    def export(
        cls,
        report_data: Dict[str, Any],
        output_path: Optional[Path] = None,
        language: Optional[str] = None,
    ) -> Path:
        lang = language or report_data.get("language", "tr")
        is_tr = lang == "tr"

        dest = Path(output_path) if output_path else (
            settings.UDI_REPORTS_DIR / "exports" / f"report_{report_data.get('database_name', 'db')}_{int(hash(report_data.get('generated_at', '')) % 1000000)}.xlsx"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)

        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # Remove default sheet

        # 1. Summary Sheet
        ws_summary = wb.create_sheet(title=t("sheet_summary", lang))
        cls._populate_summary(ws_summary, report_data, lang)

        # 2. KPIs Sheet
        ws_kpis = wb.create_sheet(title=t("sheet_kpis", lang))
        cls._populate_kpis(ws_kpis, report_data.get("kpis", []), lang)

        # 3. Trends Sheet
        ws_trends = wb.create_sheet(title=t("sheet_trends", lang))
        cls._populate_trends(ws_trends, report_data.get("trends", []), lang)

        # 4. Anomalies Sheet
        ws_anom = wb.create_sheet(title=t("sheet_anomalies", lang))
        cls._populate_anomalies(ws_anom, report_data.get("anomalies", []), lang)

        # 5. Data Quality Sheet
        ws_dq = wb.create_sheet(title=t("sheet_quality", lang))
        cls._populate_data_quality(ws_dq, report_data.get("quality", {}), lang)

        # 6. Raw Results / Rules Sheet
        ws_raw = wb.create_sheet(title=t("sheet_rules", lang))
        cls._populate_raw_results(ws_raw, report_data, lang)

        wb.save(dest)
        return dest

    @classmethod
    def _style_headers(cls, ws, row_idx: int, cols_count: int):
        for col in range(1, cols_count + 1):
            cell = ws.cell(row=row_idx, column=col)
            cell.fill = cls.HEADER_FILL
            cell.font = cls.HEADER_FONT
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = cls.THIN_BORDER

    @classmethod
    def _populate_summary(cls, ws, report: Dict[str, Any], lang: str):
        is_tr = lang == "tr"
        title = report.get("title") or t("default_report_title", lang)
        period = report.get("period") or t("default_period", lang)
        db = report.get("database_name", "")
        gen = report.get("generated_at", "")

        ws.cell(row=1, column=1, value=title).font = cls.TITLE_FONT
        ws.cell(row=2, column=1, value=f"{t('report_period', lang)}: {period} | {t('database', lang)}: {db} | {t('generated_at', lang)}: {gen}").font = cls.REGULAR_FONT

        ws.cell(row=4, column=1, value=t("sec_executive_summary", lang)).font = cls.BOLD_FONT
        row_cursor = 5
        for obs in report.get("observations", []):
            ws.cell(row=row_cursor, column=1, value=f"• {obs}").font = cls.REGULAR_FONT
            row_cursor += 1

        row_cursor += 1
        overview_title = "Veritabanı Genel Bakış" if is_tr else "Database Overview"
        ws.cell(row=row_cursor, column=1, value=overview_title).font = cls.BOLD_FONT
        row_cursor += 1
        catalog = report.get("catalog_summary", {})
        tbl_lbl = "Toplam Tablo Sayısı" if is_tr else "Total Tables"
        rec_lbl = "Toplam İncelenen Kayıt Sayısı" if is_tr else "Total Records Profiled"
        ws.cell(row=row_cursor, column=1, value=f"{tbl_lbl}: {catalog.get('table_count', 0)}").font = cls.REGULAR_FONT
        row_cursor += 1
        ws.cell(row=row_cursor, column=1, value=f"{rec_lbl}: {catalog.get('total_rows', 0):,}").font = cls.REGULAR_FONT
        ws.column_dimensions["A"].width = 85

    @classmethod
    def _populate_kpis(cls, ws, kpis: list, lang: str):
        is_tr = lang == "tr"
        if is_tr:
            headers = ["Metrik Adı", "Formül", "Mevcut Değer", "Birim", "Önceki Dönem", "Aylık Değişim (MoM %)", "Hedef Değer", "Hedef Gerçekleşme %"]
        else:
            headers = ["KPI Name", "Formula", "Current Value", "Unit", "Previous Period", "MoM Growth %", "Target Value", "Target Achievement %"]

        for c_idx, h in enumerate(headers, start=1):
            ws.cell(row=1, column=c_idx, value=h)
        cls._style_headers(ws, 1, len(headers))

        for r_idx, k in enumerate(kpis, start=2):
            k_name = localize_kpi_name(k.get("name", ""), lang)
            ws.cell(row=r_idx, column=1, value=k_name).font = cls.BOLD_FONT
            ws.cell(row=r_idx, column=2, value=k.get("formula", "")).font = cls.REGULAR_FONT
            ws.cell(row=r_idx, column=3, value=k.get("current_value", 0)).font = cls.BOLD_FONT
            ws.cell(row=r_idx, column=4, value=k.get("unit", "")).font = cls.REGULAR_FONT
            ws.cell(row=r_idx, column=5, value=k.get("previous_period_value", "-")).font = cls.REGULAR_FONT

            growth = k.get("growth_rate_mom_pct")
            if growth is not None:
                c6 = ws.cell(row=r_idx, column=6, value=float(growth) / 100.0)
                c6.number_format = "+0.0%;-0.0%;0.0%"
            else:
                c6 = ws.cell(row=r_idx, column=6, value="-")
            c6.font = cls.REGULAR_FONT

            ws.cell(row=r_idx, column=7, value=k.get("target_value", "-")).font = cls.REGULAR_FONT

            ach = k.get("target_achievement_pct")
            if ach is not None:
                c8 = ws.cell(row=r_idx, column=8, value=float(ach) / 100.0)
                c8.number_format = "0.0%"
            else:
                c8 = ws.cell(row=r_idx, column=8, value="-")
            c8.font = cls.REGULAR_FONT

        for c in ["A", "B", "C", "D", "E", "F", "G", "H"]:
            ws.column_dimensions[c].width = 24

    @classmethod
    def _populate_trends(cls, ws, trends: list, lang: str):
        is_tr = lang == "tr"
        if is_tr:
            headers = ["Metrik Adı", "Trend Yönü", "Toplam Büyüme %", "Regresyon Eğimi", "R² Değeri", "Volatilite (CV %)", "İstatistiksel Açıklama"]
        else:
            headers = ["Metric", "Trajectory", "Total Growth %", "Linear Slope", "R² Score", "Volatility (CV %)", "Statistical Explanation"]

        for c_idx, h in enumerate(headers, start=1):
            ws.cell(row=1, column=c_idx, value=h)
        cls._style_headers(ws, 1, len(headers))

        for r_idx, t_item in enumerate(trends, start=2):
            direction = localize_trend_direction(t_item.get("trend_direction", ""), lang)
            exp = t_item.get("explanation_tr") if is_tr and t_item.get("explanation_tr") else t_item.get("explanation", "")
            m_name = localize_kpi_name(t_item.get("metric_name", ""), lang)

            ws.cell(row=r_idx, column=1, value=m_name).font = cls.BOLD_FONT
            ws.cell(row=r_idx, column=2, value=direction).font = cls.REGULAR_FONT

            tot_growth = t_item.get("total_growth_percentage")
            if tot_growth is not None:
                c3 = ws.cell(row=r_idx, column=3, value=float(tot_growth) / 100.0)
                c3.number_format = "+0.0%;-0.0%;0.0%"
            else:
                c3 = ws.cell(row=r_idx, column=3, value="-")
            c3.font = cls.BOLD_FONT

            ws.cell(row=r_idx, column=4, value=t_item.get("linear_slope", 0)).font = cls.REGULAR_FONT
            ws.cell(row=r_idx, column=5, value=t_item.get("r_squared", 0)).font = cls.REGULAR_FONT

            vol = t_item.get("volatility_cv") if t_item.get("volatility_cv") is not None else t_item.get("volatility_coefficient_variation")
            if vol is not None:
                c6 = ws.cell(row=r_idx, column=6, value=float(vol) / 100.0)
                c6.number_format = "0.0%"
            else:
                c6 = ws.cell(row=r_idx, column=6, value="-")
            c6.font = cls.REGULAR_FONT

            ws.cell(row=r_idx, column=7, value=exp).font = cls.REGULAR_FONT

        ws.column_dimensions["A"].width = 24
        ws.column_dimensions["B"].width = 18
        ws.column_dimensions["C"].width = 18
        ws.column_dimensions["D"].width = 16
        ws.column_dimensions["E"].width = 14
        ws.column_dimensions["F"].width = 18
        ws.column_dimensions["G"].width = 65

    @classmethod
    def _populate_anomalies(cls, ws, anomalies: list, lang: str):
        is_tr = lang == "tr"
        if is_tr:
            headers = ["Varlık / Kayıt", "Metrik", "Önem Derecesi", "Gözlenen Değer", "Normal Aralık", "Sapma %", "Yöntem", "Açıklama"]
        else:
            headers = ["Entity", "Metric", "Severity", "Observed Value", "Normal Range", "Deviation %", "Method", "Explanation"]

        for c_idx, h in enumerate(headers, start=1):
            ws.cell(row=1, column=c_idx, value=h)
        cls._style_headers(ws, 1, len(headers))

        for r_idx, a in enumerate(anomalies, start=2):
            sev = localize_severity(a.get("severity", "LOW"), lang)
            exp = a.get("explanation_tr") if is_tr and a.get("explanation_tr") else a.get("explanation", "")
            ws.cell(row=r_idx, column=1, value=str(a.get("entity", ""))).font = cls.BOLD_FONT
            ws.cell(row=r_idx, column=2, value=str(a.get("metric", ""))).font = cls.REGULAR_FONT
            ws.cell(row=r_idx, column=3, value=sev).font = cls.BOLD_FONT
            ws.cell(row=r_idx, column=4, value=a.get("observed_value", 0)).font = cls.BOLD_FONT
            ws.cell(row=r_idx, column=5, value=str(a.get("normal_range", ""))).font = cls.REGULAR_FONT
            ws.cell(row=r_idx, column=6, value=str(a.get("deviation_pct", ""))).font = cls.REGULAR_FONT
            ws.cell(row=r_idx, column=7, value=str(a.get("method", ""))).font = cls.REGULAR_FONT
            ws.cell(row=r_idx, column=8, value=exp).font = cls.REGULAR_FONT

        ws.column_dimensions["A"].width = 20
        ws.column_dimensions["B"].width = 20
        ws.column_dimensions["C"].width = 16
        ws.column_dimensions["D"].width = 16
        ws.column_dimensions["E"].width = 22
        ws.column_dimensions["F"].width = 16
        ws.column_dimensions["G"].width = 18
        ws.column_dimensions["H"].width = 65

    @classmethod
    def _populate_data_quality(cls, ws, quality: Dict[str, Any], lang: str):
        is_tr = lang == "tr"
        if is_tr:
            headers = ["Hedef Tablo", "İncelenen Sütun", "İhlal Edilen Kural", "Önem Derecesi", "Ceza Puanı", "İhlal Sayısı", "İhlal Oranı %", "Açıklama / Mesaj"]
        else:
            headers = ["Target Table", "Column", "Rule Name", "Severity", "Penalty Pts", "Violation Count", "Violation %", "Message"]

        for c_idx, h in enumerate(headers, start=1):
            ws.cell(row=1, column=c_idx, value=h)
        cls._style_headers(ws, 1, len(headers))

        r_cursor = 2
        for t_item in quality.get("tables", []):
            for v in t_item.get("violations", []):
                sev = localize_severity(v.get("severity", "LOW"), lang)
                rule_name = v.get("rule_name_tr") if is_tr and v.get("rule_name_tr") else v.get("rule_name", "")
                msg = v.get("message_tr") if is_tr and v.get("message_tr") else v.get("message", "")

                ws.cell(row=r_cursor, column=1, value=v.get("table_name", "")).font = cls.BOLD_FONT
                ws.cell(row=r_cursor, column=2, value=v.get("column_name", "-")).font = cls.REGULAR_FONT
                ws.cell(row=r_cursor, column=3, value=rule_name).font = cls.REGULAR_FONT
                ws.cell(row=r_cursor, column=4, value=sev).font = cls.BOLD_FONT
                ws.cell(row=r_cursor, column=5, value=v.get("penalty", 0)).font = cls.REGULAR_FONT
                ws.cell(row=r_cursor, column=6, value=v.get("violation_count", 0)).font = cls.REGULAR_FONT

                v_pct = v.get("violation_percentage")
                if v_pct is not None:
                    c7 = ws.cell(row=r_cursor, column=7, value=float(v_pct) / 100.0)
                    c7.number_format = "0.0%"
                else:
                    c7 = ws.cell(row=r_cursor, column=7, value="-")
                c7.font = cls.REGULAR_FONT

                ws.cell(row=r_cursor, column=8, value=msg).font = cls.REGULAR_FONT
                r_cursor += 1

        for c in ["A", "B", "C", "D", "E", "F", "G", "H"]:
            ws.column_dimensions[c].width = 22
        ws.column_dimensions["H"].width = 50

    @classmethod
    def _populate_raw_results(cls, ws, report: Dict[str, Any], lang: str):
        is_tr = lang == "tr"
        if is_tr:
            headers = ["Kural Adı", "Hedef Tablo", "Önem Derecesi", "Koşul İfadesi", "İhlal Sayısı", "Sonuç Durumu", "Tetiklenen Mesaj"]
        else:
            headers = ["Rule Name", "Target Table", "Severity", "Condition", "Violations Count", "Status", "Triggered Message"]

        for c_idx, h in enumerate(headers, start=1):
            ws.cell(row=1, column=c_idx, value=h)
        cls._style_headers(ws, 1, len(headers))

        for r_idx, r in enumerate(report.get("rule_violations", []), start=2):
            loc_r = localize_rule(r.get("rule_name", ""), r.get("alert_message", ""), lang)
            sev = localize_severity(r.get("severity", "HIGH"), lang)
            status_text = "İHLAL" if is_tr and r.get("status") == "VIOLATION" else r.get("status", "VIOLATION")

            ws.cell(row=r_idx, column=1, value=loc_r["name"]).font = cls.BOLD_FONT
            ws.cell(row=r_idx, column=2, value=r.get("table_name", "")).font = cls.REGULAR_FONT
            ws.cell(row=r_idx, column=3, value=sev).font = cls.BOLD_FONT
            ws.cell(row=r_idx, column=4, value=r.get("condition", "")).font = cls.REGULAR_FONT
            ws.cell(row=r_idx, column=5, value=r.get("violation_count", 0)).font = cls.REGULAR_FONT
            ws.cell(row=r_idx, column=6, value=status_text).font = cls.REGULAR_FONT
            ws.cell(row=r_idx, column=7, value=loc_r["alert_message"]).font = cls.REGULAR_FONT

        for c in ["A", "B", "C", "D", "E", "F", "G"]:
            ws.column_dimensions[c].width = 24
        ws.column_dimensions["G"].width = 60
