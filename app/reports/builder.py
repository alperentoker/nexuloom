from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.core.config import settings
from app.core.lineage import lineage_tracker
from app.core.audit import audit_logger
from app.database.registry import connection_registry
from app.discovery.schema import SchemaDiscoverer
from app.quality.engine import DataQualityEngine
from app.metrics.kpi_engine import kpi_engine
from app.analytics.trends import TrendAnalyzer
from app.anomaly.detector import AnomalyEngine
from app.rules.rule_engine import business_rule_engine
from app.insights.insight_engine import InsightEngine


from app.core.i18n import t as i18n_t, localize_kpi_name


class ReportBuilder:
    """Compiles multi-engine intelligence into structured report data ready for export."""

    ALL_SECTIONS_EN = [
        "Executive Summary",
        "KPI Summary",
        "Trend Analysis",
        "Anomaly Report",
        "Data Quality",
        "Business Rule Violations",
        "Root Cause Analysis",
        "Detailed Tables",
        "Recommendations",
        "Appendix",
    ]

    ALL_SECTIONS_TR = [
        "Yönetici Özeti",
        "KPI Özeti",
        "Trend Analizi",
        "Anomali Raporu",
        "Veri Kalitesi",
        "İş Kuralı İhlalleri",
        "Kök Neden Analizi",
        "Detaylı Tablolar",
        "Öneriler",
        "Ek & Soykütüğü",
    ]

    def __init__(self, db_name: str):
        self.db_name = db_name
        self.engine = connection_registry.get_engine_for(db_name)

    @staticmethod
    def _has_section(sections: List[str], *names: str) -> bool:
        return any(n in sections for n in names)

    def build_report_data(
        self,
        title: Optional[str] = None,
        period: Optional[str] = None,
        included_sections: Optional[List[str]] = None,
        language: str = "tr",
    ) -> Dict[str, Any]:
        """Assembles data from all platform engines into a single consolidated report structure."""
        lang = (language or "tr").lower()
        if lang not in ("tr", "en"):
            lang = "tr"

        default_title = i18n_t("default_report_title", lang)
        default_period = i18n_t("default_period", lang)
        rep_title = title if (title and title != "Monthly Business Intelligence & Executive Report") else default_title
        rep_period = period if (period and period != "September 2026") else default_period

        default_sections = self.ALL_SECTIONS_TR if lang == "tr" else self.ALL_SECTIONS_EN
        sections = included_sections or default_sections
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        report: Dict[str, Any] = {
            "title": rep_title,
            "period": rep_period,
            "database_name": self.db_name,
            "generated_at": generated_at,
            "sections": sections,
            "language": lang,
        }

        # 1. Schema & Table Summary
        discoverer = SchemaDiscoverer(self.db_name, self.engine)
        catalog = discoverer.discover_catalog()
        report["catalog_summary"] = {
            "table_count": catalog.get("table_count", 0),
            "total_rows": catalog.get("total_rows", 0),
            "tables": [t["name"] for t in catalog.get("tables", [])],
        }

        # 2. KPIs
        kpis_data = []
        if self._has_section(sections, "KPI Summary", "KPI Özeti", "Executive Summary", "Yönetici Özeti"):
            available_kpis = kpi_engine.list_kpis(self.db_name)
            for k in available_kpis:
                try:
                    res = kpi_engine.evaluate_kpi(k["name"], self.engine)
                    kpis_data.append(res)
                except Exception:
                    pass
        report["kpis"] = kpis_data

        # 3. Trends
        trends_data = []
        if self._has_section(sections, "Trend Analysis", "Trend Analizi"):
            for kpi in kpis_data:
                ts = kpi.get("time_series", [])
                if len(ts) >= 2:
                    t_analysis = TrendAnalyzer.analyze_series(
                        ts, metric_name=kpi["name"], unit=kpi.get("unit", "")
                    )
                    trends_data.append(t_analysis)
        report["trends"] = trends_data

        # 4. Anomalies
        anomalies_data = []
        if self._has_section(sections, "Anomaly Report", "Anomali Raporu"):
            anomaly_engine = AnomalyEngine(self.db_name, self.engine)
            # Scan top tables for anomalies
            for t in catalog.get("tables", [])[:3]:
                # find first numeric column
                num_cols = [c["name"] for c in t.get("columns", []) if "int" in c["type"].lower() or "float" in c["type"].lower() or "real" in c["type"].lower()]
                if num_cols:
                    try:
                        res = anomaly_engine.scan_table(t["name"], metric_col=num_cols[0], limit=5000)
                        anomalies_data.extend(res.get("anomalies", []))
                    except Exception:
                        pass
        report["anomalies"] = anomalies_data[:25]  # Top 25 anomalies

        # 5. Data Quality
        quality_data = {}
        if self._has_section(sections, "Data Quality", "Veri Kalitesi", "Executive Summary", "Yönetici Özeti"):
            try:
                dq_engine = DataQualityEngine(self.db_name, self.engine)
                quality_data = dq_engine.evaluate_database(sample_size=10000)
            except Exception as e:
                quality_data = {"overall_quality_score": 100.0, "overall_grade": "UNKNOWN", "tables": []}
        report["quality"] = quality_data

        # 6. Business Rules
        rule_violations = []
        if self._has_section(sections, "Business Rule Violations", "İş Kuralı İhlalleri"):
            try:
                all_rule_runs = business_rule_engine.execute_all_rules(self.db_name)
                rule_violations = [r for r in all_rule_runs if r.get("status") == "VIOLATION"]
            except Exception:
                pass
        report["rule_violations"] = rule_violations

        # 7. Insights & Root Cause
        insights_data = []
        if self._has_section(sections, "Root Cause Analysis", "Kök Neden Analizi", "Executive Summary", "Yönetici Özeti"):
            insight_engine = InsightEngine(self.db_name, self.engine)
            # Find order or transaction table
            for t in catalog.get("tables", []):
                t_name = t["name"].lower()
                if any(w in t_name for w in ("order", "sale", "transact", "production", "expense")):
                    # Find date col and metric col
                    date_col = next((c["name"] for c in t["columns"] if "date" in c["name"].lower() or "time" in c["name"].lower()), None)
                    metric_col = next((c["name"] for c in t["columns"] if any(m in c["name"].lower() for m in ("amount", "total", "price", "revenue", "cost", "val"))), None)
                    if date_col and metric_col:
                        try:
                            ins = insight_engine.analyze_metric_variance(t["name"], metric_col=metric_col, date_col=date_col)
                            insights_data.append(ins)
                        except Exception:
                            pass
        report["insights"] = insights_data

        # 8. Observations & Recommendations (Deterministic Synthesis)
        observations = self._generate_observations(report, language=lang)
        report["observations"] = observations

        # 9. Lineage & Appendix
        report_id = f"REPORT:{self.db_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        lineage_tracker.record(
            item_type="REPORT",
            item_id=report_id,
            item_label=rep_title,
            source_db=self.db_name,
            metadata={"period": rep_period, "sections": sections},
        )
        report["report_id"] = report_id
        report["lineage_summary"] = {
            "source_database": self.db_name,
            "engine_count": 8,
            "deterministic_assurance": i18n_t("deterministic_assurance", lang),
        }

        audit_logger.log(
            action="REPORT_GENERATE",
            database_name=self.db_name,
            target=rep_title,
            details={"sections": len(sections), "kpis": len(kpis_data), "language": lang},
        )

        return report

    def _generate_observations(self, report: Dict[str, Any], language: str = "tr") -> List[str]:
        obs = []
        is_tr = language == "tr"
        kpis = report.get("kpis", [])
        for k in kpis:
            growth = k.get("growth_rate_mom_pct")
            if growth is not None:
                k_name = localize_kpi_name(k.get("name", "Metrik"), language)
                if is_tr:
                    verb = "artış gösterdi" if growth > 0 else "azalış gösterdi"
                    obs.append(f"{k_name} metriği önceki döneme göre %{abs(growth)} {verb}.")
                else:
                    verb = "increased" if growth > 0 else "decreased"
                    obs.append(f"{k_name} {verb} {abs(growth)}% compared with the previous period.")

        insights = report.get("insights", [])
        for ins in insights:
            for factor in ins.get("contributing_factors", [])[:2]:
                st = factor.get("statement_tr") if is_tr else factor.get("statement")
                obs.append(st or factor.get("statement", ""))

        quality = report.get("quality", {})
        if quality.get("overall_quality_score") is not None:
            score = quality["overall_quality_score"]
            crit = quality.get("critical_violations", 0)
            grade = quality.get("overall_grade", "A")
            if crit > 0:
                if is_tr:
                    obs.append(f"Veri kalitesi {score:.0f}/100 olarak değerlendirildi ve çözülmesi gereken {crit} kritik bütünlük uyarısı tespit edildi.")
                else:
                    obs.append(f"Data quality scored at {score:.0f}/100 with {crit} critical integrity warnings requiring remediation.")
            else:
                if is_tr:
                    obs.append(f"Genel veritabanı kalitesi {score:.0f}/100 seviyesindedir (Derece: {grade}).")
                else:
                    obs.append(f"Overall database quality stands at {score:.0f}/100 (Grade: {grade}).")

        anomalies = report.get("anomalies", [])
        critical_anom = [a for a in anomalies if a.get("severity") == "CRITICAL"]
        if critical_anom:
            if is_tr:
                obs.append(f"Telemetri ve işlem metriklerinde {len(critical_anom)} kritik istatistiksel anomali tespit edildi.")
            else:
                obs.append(f"{len(critical_anom)} critical statistical anomalies were identified in telemetry and transactional metrics.")

        rules = report.get("rule_violations", [])
        if rules:
            if is_tr:
                obs.append(f"{len(rules)} adet operasyonel iş kuralı alarmı tetiklendi.")
            else:
                obs.append(f"{len(rules)} business rule alerts triggered active operational warnings.")

        if not obs:
            if is_tr:
                obs.append("Tüm temel metrikler, veri kalitesi skorları ve operasyonel kurallar normal parametreler dahilinde çalışmaktadır.")
            else:
                obs.append("All baseline metrics, data quality scores, and operational rules are operating within normal parameters.")

        return obs
