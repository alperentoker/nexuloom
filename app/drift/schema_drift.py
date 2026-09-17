"""Schema Drift Detection Engine for tracking table structure, column, and type mutations over time."""

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.config import settings
from app.discovery.schema import SchemaDiscoverer


class SchemaDriftTracker:
    """Snapshots schema structures and detects added, removed, or mutated columns across versions."""

    def __init__(self, db_name: str, system_db_path: Optional[str] = None):
        self.db_name = db_name
        self.system_db_path = str(system_db_path or settings.SYSTEM_DB_PATH)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.system_db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    database_name TEXT NOT NULL,
                    table_name TEXT NOT NULL,
                    schema_hash TEXT NOT NULL,
                    column_count INTEGER NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_schema_snapshots_db_tbl
                ON schema_snapshots (database_name, table_name, created_at DESC)
            """)
            conn.commit()

    @staticmethod
    def _compute_schema_hash(columns: List[Dict[str, Any]]) -> str:
        """Computes a deterministic hash for table schema."""
        canonical = []
        for c in sorted(columns, key=lambda x: x["name"]):
            canonical.append(f"{c['name']}:{c.get('type', '')}:{c.get('nullable', True)}:{c.get('primary_key', False)}")
        raw = "|".join(canonical)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def take_snapshot(self) -> List[Dict[str, Any]]:
        """Discovers current catalog and persists a timestamped snapshot for each table."""
        discoverer = SchemaDiscoverer(self.db_name)
        catalog = discoverer.discover_catalog(use_cache=False)
        now = datetime.now(timezone.utc).isoformat()
        records = []

        with self._get_connection() as conn:
            for tbl in catalog.get("tables", []):
                t_name = tbl["name"]
                cols = tbl.get("columns", [])
                s_hash = self._compute_schema_hash(cols)
                cols_json = json.dumps(cols, ensure_ascii=False)

                conn.execute(
                    """
                    INSERT INTO schema_snapshots (database_name, table_name, schema_hash, column_count, snapshot_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (self.db_name, t_name, s_hash, len(cols), cols_json, now)
                )
                records.append({"table_name": t_name, "column_count": len(cols), "hash": s_hash})
            conn.commit()

        return records

    def detect_schema_drift(self) -> Dict[str, Any]:
        """Compares the latest schema against the previous baseline snapshot for all tables."""
        discoverer = SchemaDiscoverer(self.db_name)
        catalog = discoverer.discover_catalog(use_cache=False)
        current_tables = {t["name"]: t for t in catalog.get("tables", [])}

        results = []
        total_drifts = 0

        with self._get_connection() as conn:
            # Check each current table
            for tbl_name, tbl_data in current_tables.items():
                current_cols = {c["name"]: c for c in tbl_data.get("columns", [])}
                current_hash = self._compute_schema_hash(tbl_data.get("columns", []))

                # Fetch historical snapshots ordered by date DESC
                rows = conn.execute(
                    """
                    SELECT * FROM schema_snapshots
                    WHERE database_name = ? AND table_name = ?
                    ORDER BY id DESC LIMIT 2
                    """,
                    (self.db_name, tbl_name)
                ).fetchall()

                if not rows:
                    # No baseline snapshot yet, save initial baseline
                    self.take_snapshot()
                    results.append({
                        "table_name": tbl_name,
                        "drift_detected": False,
                        "status": "INITIAL_BASELINE",
                        "severity": "NONE",
                        "summary": "İlk temel şema referansı kaydedildi.",
                        "added_columns": [],
                        "removed_columns": [],
                        "modified_columns": [],
                        "baseline_date": None,
                        "current_columns_count": len(current_cols),
                    })
                    continue

                # Compare with earliest or previous baseline
                baseline_row = rows[-1]  # Older of the recent ones
                baseline_cols_list = json.loads(baseline_row["snapshot_json"])
                baseline_cols = {c["name"]: c for c in baseline_cols_list}
                baseline_date = baseline_row["created_at"]

                added = []
                for c_name, c_info in current_cols.items():
                    if c_name not in baseline_cols:
                        added.append({"name": c_name, "type": c_info.get("type")})

                removed = []
                for b_name, b_info in baseline_cols.items():
                    if b_name not in current_cols:
                        removed.append({"name": b_name, "type": b_info.get("type")})

                modified = []
                for c_name in current_cols:
                    if c_name in baseline_cols:
                        c_type = str(current_cols[c_name].get("type", "")).upper()
                        b_type = str(baseline_cols[c_name].get("type", "")).upper()
                        if c_type != b_type:
                            modified.append({
                                "name": c_name,
                                "old_type": b_type,
                                "new_type": c_type,
                            })

                drift_detected = bool(added or removed or modified)
                severity = "NONE"
                if removed:
                    severity = "CRITICAL"
                elif modified:
                    severity = "HIGH"
                elif added:
                    severity = "MEDIUM"

                if drift_detected:
                    total_drifts += 1
                    summary_parts = []
                    if added:
                        summary_parts.append(f"{len(added)} yeni kolon eklendi ({', '.join([c['name'] for c in added])})")
                    if removed:
                        summary_parts.append(f"{len(removed)} kolon silindi ({', '.join([c['name'] for c in removed])})")
                    if modified:
                        summary_parts.append(f"{len(modified)} kolon tipi değişti ({', '.join([c['name'] for c in modified])})")
                    summary = "; ".join(summary_parts)
                else:
                    summary = "Şema tamamen kararlı ve temel referansla eşleşiyor."

                results.append({
                    "table_name": tbl_name,
                    "drift_detected": drift_detected,
                    "severity": severity,
                    "status": "DRIFT_DETECTED" if drift_detected else "STABLE",
                    "summary": summary,
                    "added_columns": added,
                    "removed_columns": removed,
                    "modified_columns": modified,
                    "baseline_date": baseline_date,
                    "current_columns_count": len(current_cols),
                    "baseline_columns_count": len(baseline_cols),
                })

        return {
            "database_name": self.db_name,
            "total_tables": len(results),
            "drift_detected_count": total_drifts,
            "overall_status": "CRITICAL_DRIFT" if any(r["severity"] == "CRITICAL" for r in results) else ("DRIFT_DETECTED" if total_drifts > 0 else "STABLE"),
            "tables": results,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
