import json
from pathlib import Path
from typing import Any, Dict, Optional
from app.core.config import settings
from app.core.i18n import t, localize_kpi_name, localize_severity, localize_rule


class HTMLExporter:
    """Renders high-finish, self-contained executive HTML report with print-optimized CSS."""

    @classmethod
    def export(
        cls,
        report_data: Dict[str, Any],
        output_path: Optional[Path] = None,
        language: Optional[str] = None,
    ) -> Path:
        lang = language or report_data.get("language", "tr")
        is_tr = lang == "tr"

        dest = output_path or (
            settings.UDI_REPORTS_DIR / "exports" / f"report_{report_data.get('database_name', 'db')}_{int(hash(report_data.get('generated_at', '')) % 1000000)}.html"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)

        kpis = report_data.get("kpis", [])
        anomalies = report_data.get("anomalies", [])
        quality = report_data.get("quality", {})
        observations = report_data.get("observations", [])
        rules = report_data.get("rule_violations", [])
        insights = report_data.get("insights", [])

        # Format KPI cards
        kpi_cards_html = ""
        for k in kpis:
            val = f"{k.get('current_value', 0):,}"
            unit = k.get("unit", "")
            growth = k.get("growth_rate_mom_pct")
            growth_badge = ""
            k_name = localize_kpi_name(k.get("name", "Metric"), lang)
            if growth is not None:
                arrow = "↑" if growth > 0 else ("↓" if growth < 0 else "→")
                color = "#10b981" if growth > 0 else "#ef4444"
                vs_text = "önceki döneme göre" if is_tr else "vs prev period"
                growth_badge = f'<div style="color: {color}; font-weight: 600; font-size: 0.9rem; margin-top: 4px;">{arrow} %{abs(growth)} {vs_text}</div>'

            kpi_cards_html += f"""
            <div class="kpi-card">
                <div class="kpi-title">{k_name}</div>
                <div class="kpi-value">{unit}{val}</div>
                {growth_badge}
            </div>
            """

        # Format Observations
        observations_html = "".join([f"<li>{obs}</li>" for obs in observations])

        # Format Anomalies table
        anomaly_rows = ""
        for a in anomalies[:20]:
            sev_raw = a.get("severity", "LOW")
            sev = localize_severity(sev_raw, lang)
            sev_color = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#3b82f6"}.get(sev_raw, "#6b7280")
            exp = a.get("explanation_tr") if is_tr and a.get("explanation_tr") else a.get("explanation", "")

            anomaly_rows += f"""
            <tr>
                <td><strong>{a.get('entity', '')}</strong></td>
                <td>{a.get('metric', '')}</td>
                <td><span class="badge" style="background-color: {sev_color}22; color: {sev_color}; border: 1px solid {sev_color}44;">{sev}</span></td>
                <td>{a.get('normal_range', '')}</td>
                <td><strong>{a.get('observed_value', '')}</strong></td>
                <td>{a.get('deviation_pct', '')}</td>
                <td style="font-size: 0.85rem; color: #4b5563;">{exp}</td>
            </tr>
            """

        # Format Rules table
        rules_rows = ""
        for r in rules:
            loc_r = localize_rule(r.get("rule_name", ""), r.get("alert_message", ""), lang)
            sev_raw = r.get("severity", "HIGH")
            sev = localize_severity(sev_raw, lang)
            rules_rows += f"""
            <tr>
                <td><strong>{loc_r['name']}</strong></td>
                <td>{r.get('table_name', '')}</td>
                <td><span class="badge" style="background-color: #fee2e2; color: #b91c1c;">{sev}</span></td>
                <td><code>{r.get('condition', '')}</code></td>
                <td><strong>{r.get('violation_count', 0)}</strong></td>
                <td>{loc_r['alert_message']}</td>
            </tr>
            """

        # Format Insights
        insights_html = ""
        for ins in insights:
            headline = ins.get("headline_tr") if is_tr and ins.get("headline_tr") else ins.get("headline", "")
            disclaimer = t("causality_disclaimer", lang)
            factors = []
            for f in ins.get("contributing_factors", []):
                st = f.get("statement_tr") if is_tr and f.get("statement_tr") else f.get("statement", "")
                factors.append(f"<li>{st}</li>")
            factors_list = "".join(factors)
            insights_html += f"""
            <div class="insight-box">
                <h4>{headline}</h4>
                <ul>{factors_list}</ul>
                <div class="disclaimer">{disclaimer}</div>
            </div>
            """

        logo_file = settings.BASE_DIR / "frontend" / "img" / "logo.png"
        logo_html = ""
        if logo_file.exists():
            import base64
            b64 = base64.b64encode(logo_file.read_bytes()).decode("utf-8")
            logo_html = f'<img src="data:image/png;base64,{b64}" alt="Nexuloom" style="width: 40px; height: 40px; border-radius: 6px; object-fit: cover; margin-right: 14px; flex-shrink: 0;" />'

        html_content = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_data.get('title')}</title>
    <style>
        :root {{
            --primary: #2563eb;
            --dark: #0f172a;
            --light: #f8fafc;
            --border: #e2e8f0;
            --text: #334155;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background: #f1f5f9;
            color: var(--text);
            margin: 0;
            padding: 40px 20px;
        }}
        .report-container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 48px;
            border-radius: 8px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            border: 1px solid var(--border);
        }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 2px solid #0f172a;
            padding-bottom: 24px;
            margin-bottom: 30px;
        }}
        .header-left {{
            display: flex;
            align-items: center;
        }}
        h1 {{
            margin: 0;
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--dark);
            letter-spacing: -0.02em;
        }}
        .meta {{
            color: #64748b;
            font-size: 0.85rem;
            margin-top: 4px;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .section-title {{
            font-size: 1.15rem;
            font-weight: 600;
            color: var(--dark);
            margin: 32px 0 16px 0;
            border-bottom: 1px solid var(--border);
            padding-bottom: 8px;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background: var(--light);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 16px;
        }}
        .kpi-title {{
            font-size: 0.85rem;
            color: #64748b;
            font-weight: 500;
        }}
        .kpi-value {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--dark);
            margin-top: 4px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.875rem;
            margin-bottom: 24px;
        }}
        th, td {{
            text-align: left;
            padding: 10px 14px;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            background: #f8fafc;
            color: #475569;
            font-weight: 600;
        }}
        .observations-list {{
            padding-left: 20px;
            line-height: 1.6;
            color: #1e293b;
            margin-bottom: 24px;
        }}
        .insight-box {{
            background: #f0fdf4;
            border-left: 4px solid #10b981;
            padding: 16px 20px;
            border-radius: 4px;
            margin-bottom: 16px;
        }}
        .insight-box h4 {{
            margin: 0 0 8px 0;
            color: #065f46;
            font-size: 1rem;
        }}
        .insight-box ul {{
            margin: 0;
            padding-left: 20px;
            color: #1f2937;
            font-size: 0.9rem;
            line-height: 1.5;
        }}
        .disclaimer {{
            font-size: 0.75rem;
            color: #6b7280;
            font-style: italic;
            margin-top: 8px;
        }}
        footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            font-size: 0.75rem;
            color: #94a3b8;
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .report-container {{ border: none; box-shadow: none; padding: 0; }}
        }}
    </style>
</head>
<body>
    <div class="report-container">
        <header>
            <div class="header-left">
                {logo_html}
                <div>
                    <h1>{report_data.get('title')}</h1>
                    <div class="meta">{t('report_period', lang)}: <strong>{report_data.get('period')}</strong> | {t('database', lang)}: <strong>{report_data.get('database_name')}</strong></div>
                </div>
            </div>
            <div style="text-align: right;">
                <div class="badge" style="background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd;">{t('production_quality', lang)}</div>
                <div class="meta" style="margin-top: 6px;">{t('generated_at', lang)}: {report_data.get('generated_at')}</div>
            </div>
        </header>

        <div class="section-title">{t('sec_executive_summary', lang)}</div>
        <ul class="observations-list">
            {observations_html}
        </ul>

        <div class="section-title">{t('kpi_summary_title', lang)}</div>
        <div class="kpi-grid">
            {kpi_cards_html}
        </div>

        <div class="section-title">{t('sec_data_quality', lang)}</div>
        <div style="background: #f8fafc; border: 1px solid var(--border); padding: 20px; border-radius: 8px; display: flex; justify-content: space-around; align-items: center; margin-bottom: 24px;">
            <div style="text-align: center;">
                <div style="font-size: 2.5rem; font-weight: 800; color: #10b981;">{quality.get('overall_quality_score', 100):.0f}/100</div>
                <div class="meta">{t('overall_quality_score', lang)} ({t('quality_grade', lang)}: {quality.get('overall_grade', 'A')})</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 1.8rem; font-weight: 700; color: #ef4444;">{quality.get('critical_violations', 0)}</div>
                <div class="meta">{t('critical_violations', lang)}</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 1.8rem; font-weight: 700; color: var(--primary);">{quality.get('tables_analyzed', 0)}</div>
                <div class="meta">{t('tables_analyzed', lang)}</div>
            </div>
        </div>

        <div class="section-title">{t('insights_title', lang)}</div>
        {insights_html if insights_html else f'<p style="color: #64748b;">{t("obs_all_normal", lang)}</p>'}

        <div class="section-title">{t('anom_title', lang)}</div>
        <table>
            <thead>
                <tr>
                    <th>{t('col_entity', lang)}</th>
                    <th>{t('col_metric', lang)}</th>
                    <th>{t('col_severity', lang)}</th>
                    <th>{t('col_normal_range', lang)}</th>
                    <th>{t('col_observed', lang)}</th>
                    <th>{t('col_deviation', lang)}</th>
                    <th>{t('col_explanation', lang)}</th>
                </tr>
            </thead>
            <tbody>
                {anomaly_rows or f'<tr><td colspan="7" style="color: #10b981;">{t("anom_empty", lang)}</td></tr>'}
            </tbody>
        </table>

        <div class="section-title">{t('rules_title', lang)}</div>
        <table>
            <thead>
                <tr>
                    <th>{t('col_rule_name', lang)}</th>
                    <th>{t('col_target_table', lang)}</th>
                    <th>{t('col_severity', lang)}</th>
                    <th>{t('col_condition', lang)}</th>
                    <th>{t('col_violations', lang)}</th>
                    <th>{t('col_triggered_msg', lang)}</th>
                </tr>
            </thead>
            <tbody>
                {rules_rows or f'<tr><td colspan="6" style="color: #10b981;">{t("rules_empty", lang)}</td></tr>'}
            </tbody>
        </table>

        <footer>
            <div>{t('footer_note', lang)}</div>
            <div>ID: {report_data.get('report_id', '')}</div>
        </footer>
    </div>
</body>
</html>
"""
        with open(dest, "w", encoding="utf-8") as f:
            f.write(html_content)

        return dest
