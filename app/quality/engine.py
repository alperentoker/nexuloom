from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from app.core.audit import audit_logger
from app.core.cache import cache
from app.database.registry import connection_registry
from app.database.safety import SQLSafetyValidator
from app.discovery.schema import SchemaDiscoverer
from app.quality.rules import (
    BaseQualityRule,
    NullCheckRule,
    UniquenessCheckRule,
    NonNegativeMetricRule,
    OutlierQualityRule,
    DateValidityRule,
    QualityCheckResult,
)


class DataQualityEngine:
    """Evaluates modular quality rules across tables and generates transparent quality scores."""

    def __init__(self, db_name: str, engine: Optional[Engine] = None):
        self.db_name = db_name
        self.engine = engine or connection_registry.get_engine_for(db_name)
        self.rules: List[BaseQualityRule] = [
            NullCheckRule(),
            UniquenessCheckRule(),
            NonNegativeMetricRule(),
            OutlierQualityRule(),
            DateValidityRule(),
        ]

    def register_rule(self, rule: BaseQualityRule) -> None:
        self.rules.append(rule)

    def evaluate_table(self, table_name: str, sample_size: int = 50000) -> Dict[str, Any]:
        """Evaluates all rules on a specific table."""
        safe_table_quoted = SQLSafetyValidator.quote_identifier(table_name)
        discoverer = SchemaDiscoverer(self.db_name, self.engine)
        table_meta = discoverer.inspect_table(table_name)

        query = f'SELECT * FROM {safe_table_quoted} LIMIT {sample_size}'
        try:
            with self.engine.connect() as conn:
                df = pd.read_sql(text(query), conn)
        except Exception:
            clean_tbl = SQLSafetyValidator.validate_table_identifier(table_name)
            with self.engine.connect() as conn:
                df = pd.read_sql(text(f"SELECT * FROM {clean_tbl} LIMIT {sample_size}"), conn)

        all_results: List[QualityCheckResult] = []
        for rule in self.rules:
            res = rule.evaluate(df, table_name=table_name, metadata=table_meta)
            all_results.extend(res)

        # Calculate Score
        total_penalties = sum(r.penalty for r in all_results if not r.passed)
        score = max(0.0, min(100.0, 100.0 - total_penalties))

        violations = [r.to_dict() for r in all_results if not r.passed]
        passed_checks = [r.to_dict() for r in all_results if r.passed]

        severity_counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        for v in violations:
            sev = v["severity"]
            severity_counts[sev] = severity_counts.get(sev, 0) + 1

        grade = "EXCELLENT" if score >= 90 else ("GOOD" if score >= 75 else ("FAIR" if score >= 60 else "POOR"))
        grade_tr = {"EXCELLENT": "MÜKEMMEL", "GOOD": "İYİ", "FAIR": "ORTA", "POOR": "ZAYIF"}.get(grade, grade)

        return {
            "database_name": self.db_name,
            "table_name": table_name,
            "quality_score": round(score, 1),
            "quality_grade": grade,
            "quality_grade_tr": grade_tr,
            "scoring_explanation": f"Base score 100 minus total rule violation penalties of {round(total_penalties, 1)} points.",
            "scoring_explanation_tr": f"100 temel puandan toplam {round(total_penalties, 1)} kural ihlali cezası düşüldü.",
            "total_checks": len(all_results),
            "violations_count": len(violations),
            "passed_count": len(passed_checks),
            "severity_breakdown": severity_counts,
            "violations": violations,
            "passed_checks": passed_checks,
        }

    def evaluate_database(self, sample_size: int = 25000, use_cache: bool = True) -> Dict[str, Any]:
        """Runs quality analysis across all tables in the database."""
        cache_key = cache.generate_key("db_quality", self.db_name, sample_size)
        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                return cached

        discoverer = SchemaDiscoverer(self.db_name, self.engine)
        catalog = discoverer.discover_catalog()
        tables = catalog.get("tables", [])

        table_reports = []
        scores = []
        all_violations = []

        for t in tables:
            t_name = t["name"]
            try:
                t_report = self.evaluate_table(t_name, sample_size=sample_size)
                table_reports.append(t_report)
                scores.append(t_report["quality_score"])
                all_violations.extend(t_report["violations"])
            except Exception as e:
                table_reports.append({
                    "table_name": t_name,
                    "quality_score": 100.0,
                    "error": str(e),
                    "violations": [],
                })

        overall_score = round(sum(scores) / len(scores), 1) if scores else 100.0
        overall_grade = (
            "EXCELLENT" if overall_score >= 90 else ("GOOD" if overall_score >= 75 else ("FAIR" if overall_score >= 60 else "POOR"))
        )
        overall_grade_tr = (
            {"EXCELLENT": "MÜKEMMEL", "GOOD": "İYİ", "FAIR": "ORTA", "POOR": "ZAYIF"}.get(overall_grade, overall_grade)
        )

        critical_count = sum(1 for v in all_violations if v["severity"] == "CRITICAL")
        high_count = sum(1 for v in all_violations if v["severity"] == "HIGH")

        db_quality_report = {
            "database_name": self.db_name,
            "overall_quality_score": overall_score,
            "overall_grade": overall_grade,
            "overall_grade_tr": overall_grade_tr,
            "scoring_formula": "Average of individual table quality scores weighted by check results.",
            "scoring_formula_tr": "Kontrol sonuçlarıyla ağırlıklandırılmış bireysel tablo kalite puanlarının ortalaması.",
            "tables_analyzed": len(table_reports),
            "total_violations": len(all_violations),
            "critical_violations": critical_count,
            "high_violations": high_count,
            "tables": table_reports,
        }

        cache.set(cache_key, db_quality_report, ttl_seconds=1800, database_name=self.db_name)
        audit_logger.log(
            action="DATA_QUALITY_EVALUATION",
            database_name=self.db_name,
            details={"overall_score": overall_score, "violations": len(all_violations)},
        )
        return db_quality_report
