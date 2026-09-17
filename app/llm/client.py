import json
from typing import Any, Dict, Optional, Tuple
import requests
from app.core.config import settings
from app.database.safety import SQLSafetyValidator, SQLSafetyError
from app.llm.fallback import DeterministicFallbackEngine


class LocalLLMClient:
    """Interfaces with optional local LLMs (e.g. Ollama) with strict deterministic fallback."""

    def __init__(
        self,
        enabled: Optional[bool] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self.enabled = settings.UDI_LLM_ENABLED if enabled is None else enabled
        self.api_url = api_url or settings.UDI_LLM_API_URL
        self.model = model or settings.UDI_LLM_MODEL

    def is_available(self) -> bool:
        if not self.enabled:
            return False
        try:
            # Check if ollama or compatible server responds
            base_url = self.api_url.rsplit("/api", 1)[0]
            resp = requests.get(base_url, timeout=1.5)
            return resp.status_code == 200
        except Exception:
            return False

    def generate_sql_from_nl(
        self,
        prompt: str,
        catalog: Dict[str, Any],
    ) -> Tuple[str, str, bool]:
        """Translates natural language to safe read-only SQL.
        Returns (sql_query, explanation, is_llm_used).
        """
        # If LLM is available and enabled, query Ollama
        if self.is_available():
            try:
                schema_context = self._format_catalog_context(catalog)
                system_prompt = (
                    "You are a strict read-only SQL generator. Generate ONLY one valid standard SQL SELECT or WITH query. "
                    "Do NOT use markdown code blocks, backticks, or any explanation. "
                    "NEVER use INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE. "
                    f"Schema:\n{schema_context}"
                )
                payload = {
                    "model": self.model,
                    "prompt": f"{system_prompt}\nUser Question: {prompt}\nSQL Query:",
                    "stream": False,
                }
                resp = requests.post(self.api_url, json=payload, timeout=10)
                if resp.status_code == 200:
                    raw_sql = resp.json().get("response", "").strip()
                    # Clean markdown wrappers if LLM returned them
                    raw_sql = raw_sql.replace("```sql", "").replace("```", "").strip()
                    is_safe, err = SQLSafetyValidator.validate_read_only(raw_sql)
                    if is_safe:
                        return raw_sql, "Generated via Local LLM and validated by safety engine.", True
            except Exception:
                pass

        # Deterministic fallback engine
        sql, expl = DeterministicFallbackEngine.match_nl_to_sql(prompt, catalog)
        if sql:
            return sql, expl, False
        else:
            first_tbl = catalog.get("tables", [{}])[0].get("name", "data")
            return f'SELECT * FROM "{first_tbl}" LIMIT 50', "Default table inspection query (offline fallback).", False

    def explain_metric_or_report(self, report_data: Dict[str, Any]) -> str:
        """Generates executive narrative. Falls back to deterministic synthesis if offline."""
        if self.is_available():
            try:
                obs_summary = "\n".join(report_data.get("observations", []))
                kpi_summary = "\n".join([f"{k['name']}: {k.get('current_value')}" for k in report_data.get("kpis", [])])
                prompt = (
                    "Provide a professional 2-paragraph executive summary based on these verified facts and numbers only. "
                    "Do NOT make up any numbers or change values:\n"
                    f"Facts:\n{obs_summary}\nKPIs:\n{kpi_summary}"
                )
                payload = {"model": self.model, "prompt": prompt, "stream": False}
                resp = requests.post(self.api_url, json=payload, timeout=12)
                if resp.status_code == 200:
                    text_res = resp.json().get("response", "").strip()
                    if text_res:
                        return text_res
            except Exception:
                pass

        return DeterministicFallbackEngine.generate_narrative_summary(report_data)

    def _format_catalog_context(self, catalog: Dict[str, Any]) -> str:
        lines = []
        for t in catalog.get("tables", [])[:10]:
            cols = [f"{c['name']} ({c['type']})" for c in t.get("columns", [])[:8]]
            lines.append(f"Table {t['name']}: {', '.join(cols)}")
        return "\n".join(lines)


llm_client = LocalLLMClient()
