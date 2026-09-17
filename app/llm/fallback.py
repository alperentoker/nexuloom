import re
from typing import Any, Dict, List, Optional, Tuple


class DeterministicFallbackEngine:
    """Provides deterministic rule-based Natural-Language-to-SQL mapping and structured narrative generation."""

    @classmethod
    def generate_narrative_summary(cls, report_data: Dict[str, Any]) -> str:
        """Generates executive summary paragraphs strictly using pre-computed deterministic values."""
        title = report_data.get("title", "Executive Report")
        period = report_data.get("period", "Current Period")
        kpis = report_data.get("kpis", [])
        quality = report_data.get("quality", {})
        anomalies = report_data.get("anomalies", [])
        rules = report_data.get("rule_violations", [])

        summary_parts = []
        summary_parts.append(
            f"This {title} provides a deterministic evaluation of operational performance for {period}."
        )

        if kpis:
            kpi_strs = []
            for k in kpis[:3]:
                val = f"{k.get('unit', '')}{k.get('current_value', 0):,}"
                growth = k.get("growth_rate_mom_pct")
                if growth is not None:
                    verb = "up" if growth > 0 else "down"
                    kpi_strs.append(f"{k.get('name')} at {val} ({verb} {abs(growth)}% MoM)")
                else:
                    kpi_strs.append(f"{k.get('name')} at {val}")
            summary_parts.append("Key metrics tracked: " + ", ".join(kpi_strs) + ".")

        score = quality.get("overall_quality_score", 100)
        grade = quality.get("overall_grade", "GOOD")
        summary_parts.append(
            f"Database integrity stands at {score}/100 ({grade}) across {quality.get('tables_analyzed', 0)} analyzed tables."
        )

        if anomalies:
            crit = sum(1 for a in anomalies if a.get("severity") == "CRITICAL")
            summary_parts.append(
                f"Statistical telemetry detected {len(anomalies)} anomalies, including {crit} critical deviations requiring operational review."
            )

        if rules:
            summary_parts.append(
                f"{len(rules)} business rule violation alerts are active and logged in the audit trail."
            )

        return " ".join(summary_parts)

    @classmethod
    def match_nl_to_sql(
        cls,
        nl_query: str,
        catalog: Dict[str, Any],
    ) -> Tuple[Optional[str], str]:
        """Maps common natural language business queries into safe read-only SQL deterministically."""
        q = nl_query.lower().strip()
        tables = [t["name"] for t in catalog.get("tables", [])]
        t_map = {t.lower(): t for t in tables}

        # 1. Top records by metric: "top 10 products by price"
        top_match = re.search(r"top\s+(\d+)\s+([a-z_]+)\s+by\s+([a-z_]+)", q)
        if top_match:
            n_rows = int(top_match.group(1))
            cand_tbl = top_match.group(2)
            cand_col = top_match.group(3)
            # Find matching table
            for tbl in tables:
                if cand_tbl in tbl.lower():
                    # check col in table
                    t_info = next((t for t in catalog["tables"] if t["name"] == tbl), None)
                    if t_info:
                        col_match = next((c["name"] for c in t_info["columns"] if cand_col in c["name"].lower()), None)
                        if col_match:
                            sql = f'SELECT * FROM "{tbl}" ORDER BY "{col_match}" DESC LIMIT {n_rows}'
                            return sql, f"Deterministic match: Top {n_rows} in {tbl} sorted by {col_match} descending."

        # 2. Defect / Maintenance queries: "show defects" or "machines with maintenance"
        if any(w in q for w in ("defect", "broken", "scrap")):
            for tbl in tables:
                if any(w in tbl.lower() for w in ("production", "quality", "machine")):
                    t_info = next((t for t in catalog["tables"] if t["name"] == tbl), None)
                    if t_info:
                        defect_col = next((c["name"] for c in t_info["columns"] if any(w in c["name"].lower() for w in ("defect", "fail", "scrap"))), None)
                        if defect_col:
                            sql = f'SELECT * FROM "{tbl}" WHERE "{defect_col}" > 0 ORDER BY "{defect_col}" DESC LIMIT 100'
                            return sql, f"Deterministic match: Identified defect records from {tbl}."

        # 3. Monthly / Time trend: "monthly sales" or "sales by month"
        if any(w in q for w in ("trend", "monthly", "by month", "sales")):
            for tbl in tables:
                if any(w in tbl.lower() for w in ("order", "sale", "transact")):
                    t_info = next((t for t in catalog["tables"] if t["name"] == tbl), None)
                    if t_info:
                        date_col = next((c["name"] for c in t_info["columns"] if "date" in c["name"].lower() or "time" in c["name"].lower()), None)
                        amt_col = next((c["name"] for c in t_info["columns"] if any(a in c["name"].lower() for a in ("amount", "total", "price"))), None)
                        if date_col and amt_col:
                            sql = f'SELECT "{date_col}", SUM("{amt_col}") as total_amount, COUNT(*) as count FROM "{tbl}" GROUP BY "{date_col}" ORDER BY "{date_col}" DESC LIMIT 30'
                            return sql, f"Deterministic match: Aggregated chronological sales trend from {tbl}."

        # 4. Low inventory / Stockout queries: "low inventory" or "minimum stock"
        if any(w in q for w in ("inventory", "stock", "warehouse")):
            for tbl in tables:
                if "inventory" in tbl.lower() or "stock" in tbl.lower():
                    t_info = next((t for t in catalog["tables"] if t["name"] == tbl), None)
                    if t_info:
                        cols = [c["name"].lower() for c in t_info["columns"]]
                        if "quantity" in cols and "minimum_stock" in cols:
                            sql = f'SELECT * FROM "{tbl}" WHERE quantity < minimum_stock LIMIT 100'
                            return sql, f"Deterministic match: Low stock items below minimum threshold from {tbl}."

        # 5. General table query fallback: "show customers", "list orders"
        for tbl in tables:
            if tbl.lower() in q or tbl.lower()[:-1] in q:
                sql = f'SELECT * FROM "{tbl}" LIMIT 50'
                return sql, f"Deterministic match: Selecting first 50 sample records from table '{tbl}'."

        # Default fallback to first table
        if tables:
            first_tbl = tables[0]
            sql = f'SELECT * FROM "{first_tbl}" LIMIT 25'
            return sql, f"Generic sample query on primary table '{first_tbl}'."

        return None, "Unable to map natural language to a known table schema deterministically."
