import json
from pathlib import Path
from typing import Any, Dict, Optional
from app.core.config import settings


class HTMLExporter:
    """Renders high-finish, self-contained executive HTML report with print-optimized CSS."""

    @classmethod
    def export(cls, report_data: Dict[str, Any], output_path: Optional[Path] = None) -> Path:
        dest = output_path or (
            settings.UDI_REPORTS_DIR / "exports" / f"report_{report_data.get('database_name', 'db')}_{int(hash(report_data.get('generated_at', '')) % 1000000)}.html"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)

        kpis = report_data.get("kpis", [])
        anomalies = report_data.get("anomalies", [])
        quality = report_data.get("quality", {})
        observations = report_data.get("observations", [])
        trends = report_data.get("trends", [])
        rules = report_data.get("rule_violations", [])
        insights = report_data.get("insights", [])

        # Format KPI cards
        kpi_cards_html = ""
        for k in kpis:
            val = f"{k.get('current_value', 0):,}"
            unit = k.get("unit", "")
            growth = k.get("growth_rate_mom_pct")
            growth_badge = ""
            if growth is not None:
                arrow = "↑" if growth > 0 else ("↓" if growth < 0 else "→")
                color = "#10b981" if growth > 0 else "#ef4444"
                growth_badge = f'<div style="color: {color}; font-weight: 600; font-size: 0.9rem; margin-top: 4px;">{arrow} {abs(growth)}% vs prev period</div>'

            kpi_cards_html += f"""
            <div class="kpi-card">
                <div class="kpi-title">{k.get('name', 'Metric')}</div>
                <div class="kpi-value">{unit}{val}</div>
                {growth_badge}
            </div>
            """

        # Format Observations
        observations_html = "".join([f"<li>{obs}</li>" for obs in observations])

        # Format Anomalies table
        anomaly_rows = ""
        for a in anomalies[:15]:
            sev = a.get("severity", "LOW")
            sev_color = {"CRITICAL": "#ef4444", "HIGH": "#f97316", "MEDIUM": "#eab308", "LOW": "#3b82f6"}.get(sev, "#6b7280")
            anomaly_rows += f"""
            <tr>
                <td><strong>{a.get('entity', '')}</strong></td>
                <td>{a.get('metric', '')}</td>
                <td><span class="badge" style="background-color: {sev_color}22; color: {sev_color}; border: 1px solid {sev_color}44;">{sev}</span></td>
                <td>{a.get('normal_range', '')}</td>
                <td><strong>{a.get('observed_value', '')}</strong></td>
                <td>{a.get('deviation_pct', '')}</td>
                <td style="font-size: 0.85rem; color: #4b5563;">{a.get('explanation', '')}</td>
            </tr>
            """

        # Format Rules table
        rules_rows = ""
        for r in rules:
            rules_rows += f"""
            <tr>
                <td><strong>{r.get('rule_name', '')}</strong></td>
                <td>{r.get('table_name', '')}</td>
                <td><span class="badge" style="background-color: #fee2e2; color: #b91c1c;">{r.get('severity', 'HIGH')}</span></td>
                <td>{r.get('condition', '')}</td>
                <td><strong>{r.get('violation_count', 0)}</strong></td>
                <td>{r.get('alert_message', '')}</td>
            </tr>
            """

        # Format Insights
        insights_html = ""
        for ins in insights:
            factors_list = "".join([f"<li>{f.get('statement')}</li>" for f in ins.get("contributing_factors", [])])
            insights_html += f"""
            <div class="insight-box">
                <h4>{ins.get('headline')}</h4>
                <ul>{factors_list}</ul>
                <div class="disclaimer">{ins.get('causality_disclaimer', '')}</div>
            </div>
            """

        logo_file = settings.BASE_DIR / "frontend" / "img" / "logo.png"
        logo_html = ""
        if logo_file.exists():
            import base64
            b64 = base64.b64encode(logo_file.read_bytes()).decode("utf-8")
            logo_html = f'<img src="data:image/png;base64,{b64}" alt="Nexuloom" style="width: 40px; height: 40px; border-radius: 6px; object-fit: cover; margin-right: 14px; flex-shrink: 0;" />'

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{report_data.get('title', 'Business Intelligence Report')}</title>
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
            padding: 16px;
            border-radius: 6px;
        }}
        .kpi-title {{ font-size: 0.8rem; color: #64748b; font-weight: 500; }}
        .kpi-value {{ font-size: 1.6rem; font-weight: 700; color: var(--dark); margin: 6px 0; }}
        .insight-box {{
            background: #eff6ff;
            border: 1px solid #bfdbfe;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 16px;
        }}
        .insight-box h4 {{
            margin: 0 0 10px 0;
            color: #1e40af;
        }}
        .disclaimer {{
            font-size: 0.8rem;
            color: #6b7280;
            font-style: italic;
            margin-top: 10px;
        }}
        .observations-list {{
            background: var(--light);
            border: 1px solid var(--border);
            padding: 20px 20px 20px 40px;
            border-radius: 6px;
            line-height: 1.6;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85rem;
            margin-bottom: 24px;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid var(--border);
        }}
        th {{
            background: #f8fafc;
            color: #475569;
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        footer {{
            margin-top: 40px;
            border-top: 1px solid var(--border);
            padding-top: 20px;
            font-size: 0.75rem;
            color: #94a3b8;
            display: flex;
            justify-content: space-between;
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .report-container {{ box-shadow: none; border: none; padding: 0; }}
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
                    <div class="meta">Report Period: <strong>{report_data.get('period')}</strong> | Database: <strong>{report_data.get('database_name')}</strong></div>
                </div>
            </div>
            <div style="text-align: right;">
                <div class="badge" style="background: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd;">Production Quality</div>
                <div class="meta" style="margin-top: 6px;">Generated: {report_data.get('generated_at')}</div>
            </div>
        </header>

        <div class="section-title">Key Executive Observations</div>
        <ul class="observations-list">
            {observations_html}
        </ul>

        <div class="section-title">Key Performance Indicators (KPIs)</div>
        <div class="kpi-grid">
            {kpi_cards_html}
        </div>

        <div class="section-title">Data Quality Health Summary</div>
        <div style="background: #f8fafc; border: 1px solid var(--border); padding: 20px; border-radius: 8px; display: flex; justify-content: space-around; align-items: center;">
            <div style="text-align: center;">
                <div style="font-size: 2.5rem; font-weight: 800; color: #10b981;">{quality.get('overall_quality_score', 100)}/100</div>
                <div class="meta">Overall Quality Score ({quality.get('overall_grade', 'GOOD')})</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 1.8rem; font-weight: 700; color: #ef4444;">{quality.get('critical_violations', 0)}</div>
                <div class="meta">Critical Integrity Checks</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 1.8rem; font-weight: 700; color: var(--primary);">{quality.get('tables_analyzed', 0)}</div>
                <div class="meta">Tables Profiled</div>
            </div>
        </div>

        <div class="section-title">Attribution & Diagnostic Insights</div>
        {insights_html}

        <div class="section-title">Statistical Anomalies Detected</div>
        <table>
            <thead>
                <tr>
                    <th>Entity</th>
                    <th>Metric</th>
                    <th>Severity</th>
                    <th>Normal Range</th>
                    <th>Observed</th>
                    <th>Deviation</th>
                    <th>Explanation</th>
                </tr>
            </thead>
            <tbody>
                {anomaly_rows or '<tr><td colspan="7">No critical statistical anomalies detected.</td></tr>'}
            </tbody>
        </table>

        <div class="section-title">Business Rule Evaluations</div>
        <table>
            <thead>
                <tr>
                    <th>Rule Name</th>
                    <th>Table</th>
                    <th>Severity</th>
                    <th>Condition</th>
                    <th>Violations</th>
                    <th>Alert Message</th>
                </tr>
            </thead>
            <tbody>
                {rules_rows or '<tr><td colspan="6">All operational business rules satisfied. No violations detected.</td></tr>'}
            </tbody>
        </table>

        <footer>
            <div>Nexuloom Data Intelligence Platform | Deterministic Analytics Engine</div>
            <div>Report ID: {report_data.get('report_id', '')}</div>
        </footer>
    </div>
</body>
</html>
"""
        with open(dest, "w", encoding="utf-8") as f:
            f.write(html_content)

        return dest
