import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine
from app.core.config import settings
from app.core.audit import audit_logger
from app.database.registry import connection_registry
from app.database.safety import SQLSafetyValidator, SQLSafetyError


class BusinessRuleEngine:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or settings.SYSTEM_DB_PATH)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS business_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    database_name TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    condition_sql TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    alert_message TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    last_run_at TEXT,
                    last_violations_count INTEGER DEFAULT 0
                )
            """)
            conn.commit()

    def create_rule(
        self,
        name: str,
        database_name: str,
        table_name: str,
        condition_sql: str,
        severity: str = "HIGH",
        alert_message: str = "Business condition violated.",
    ) -> Dict[str, Any]:
        # Validate table name
        safe_table = SQLSafetyValidator.validate_table_identifier(table_name)

        # Validate condition for dangerous keywords and injection
        is_safe, err = SQLSafetyValidator.validate_condition_sql(condition_sql)
        if not is_safe:
            raise SQLSafetyError(f"Unsafe business rule condition: {err}")

        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO business_rules (
                    name, database_name, table_name, condition_sql,
                    severity, alert_message, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (name, database_name, safe_table, condition_sql, severity.upper(), alert_message, now),
            )
            conn.commit()

        audit_logger.log(
            action="RULE_CREATE",
            database_name=database_name,
            target=name,
            details={"table": safe_table, "condition": condition_sql, "severity": severity},
        )
        return self.get_rule(name)

    def get_rule(self, name: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM business_rules WHERE name = ?", (name,)).fetchone()
            return dict(row) if row else None

    def list_rules(self, database_name: Optional[str] = None) -> List[Dict[str, Any]]:
        query = "SELECT * FROM business_rules WHERE 1=1"
        params = []
        if database_name:
            query += " AND database_name = ?"
            params.append(database_name)
        query += " ORDER BY id DESC"

        with self._get_connection() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    def toggle_rule(self, name: str, is_active: bool) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "UPDATE business_rules SET is_active = ? WHERE name = ?",
                (1 if is_active else 0, name),
            )
            conn.commit()
            return cursor.rowcount > 0

    def delete_rule(self, name: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.execute("DELETE FROM business_rules WHERE name = ?", (name,))
            conn.commit()
            return cursor.rowcount > 0

    def execute_rule(self, name: str, engine: Optional[Engine] = None, limit: int = 500) -> Dict[str, Any]:
        """Evaluates condition and captures violating rows."""
        rule = self.get_rule(name)
        if not rule:
            raise ValueError(f"Rule '{name}' does not exist.")

        db_name = rule["database_name"]
        table_name = rule["table_name"]
        condition = rule["condition_sql"]
        eng = engine or connection_registry.get_engine_for(db_name)

        # Validate identifiers and condition
        safe_table_quoted = SQLSafetyValidator.quote_identifier(table_name)
        is_safe, err = SQLSafetyValidator.validate_condition_sql(condition)
        if not is_safe:
            raise SQLSafetyError(f"Unsafe business rule condition: {err}")

        query = f'SELECT * FROM {safe_table_quoted} WHERE {condition} LIMIT {limit}'
        try:
            with eng.connect() as conn:
                df = pd.read_sql(text(query), conn)
        except Exception:
            clean_tbl = SQLSafetyValidator.validate_table_identifier(table_name)
            with eng.connect() as conn:
                df = pd.read_sql(text(f"SELECT * FROM {clean_tbl} WHERE {condition} LIMIT {limit}"), conn)


        violation_count = len(df)
        violations = df.to_dict(orient="records")
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            conn.execute(
                "UPDATE business_rules SET last_run_at = ?, last_violations_count = ? WHERE name = ?",
                (now, violation_count, name),
            )
            conn.commit()

        status = "VIOLATION" if violation_count > 0 else "PASSED"
        audit_logger.log(
            action="RULE_EXECUTE",
            status=status,
            database_name=db_name,
            target=name,
            query_text=query,
            details={"violations_found": violation_count, "severity": rule["severity"]},
        )

        return {
            "rule_name": name,
            "database_name": db_name,
            "table_name": table_name,
            "condition": condition,
            "severity": rule["severity"],
            "alert_message": rule["alert_message"],
            "status": status,
            "violation_count": violation_count,
            "sample_violations": violations[:20],
            "executed_at": now,
        }

    def execute_all_rules(self, database_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Executes all active rules."""
        rules = self.list_rules(database_name)
        results = []
        for r in rules:
            if r["is_active"]:
                try:
                    res = self.execute_rule(r["name"])
                    results.append(res)
                except Exception as e:
                    results.append({
                        "rule_name": r["name"],
                        "status": "ERROR",
                        "error": str(e),
                        "violation_count": 0,
                    })
        return results


business_rule_engine = BusinessRuleEngine()
