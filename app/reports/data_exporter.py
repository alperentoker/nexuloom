import csv
import json
from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd
from app.core.config import settings


class DataExporter:
    """Exports intelligence reports to JSON and CSV formats."""

    @classmethod
    def export_json(cls, report_data: Dict[str, Any], output_path: Optional[Path] = None) -> Path:
        dest = output_path or (
            settings.UDI_REPORTS_DIR / "exports" / f"report_{report_data.get('database_name', 'db')}_{int(hash(report_data.get('generated_at', '')) % 1000000)}.json"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2, default=str)
        return dest

    @classmethod
    def export_csv(cls, report_data: Dict[str, Any], output_path: Optional[Path] = None) -> Path:
        """Flattens KPIs and anomalies into a consolidated tabular CSV report."""
        dest = output_path or (
            settings.UDI_REPORTS_DIR / "exports" / f"report_{report_data.get('database_name', 'db')}_{int(hash(report_data.get('generated_at', '')) % 1000000)}.csv"
        )
        dest.parent.mkdir(parents=True, exist_ok=True)

        rows = []
        # KPIs
        for k in report_data.get("kpis", []):
            rows.append({
                "Category": "KPI",
                "Item": k.get("name"),
                "Metric_Value": k.get("current_value"),
                "Unit": k.get("unit"),
                "Status": f"MoM: {k.get('growth_rate_mom_pct')}%" if k.get("growth_rate_mom_pct") else "Current",
                "Details": k.get("formula"),
            })

        # Anomalies
        for a in report_data.get("anomalies", []):
            rows.append({
                "Category": "Anomaly",
                "Item": f"{a.get('entity')} - {a.get('metric')}",
                "Metric_Value": a.get("observed_value"),
                "Unit": a.get("deviation_pct"),
                "Status": a.get("severity"),
                "Details": a.get("explanation"),
            })

        # Rules
        for r in report_data.get("rule_violations", []):
            rows.append({
                "Category": "Business Rule Violation",
                "Item": r.get("rule_name"),
                "Metric_Value": r.get("violation_count"),
                "Unit": "violations",
                "Status": r.get("severity"),
                "Details": r.get("alert_message"),
            })

        df = pd.DataFrame(rows)
        df.to_csv(dest, index=False, encoding="utf-8")
        return dest
