"""FastAPI routes for Schema Drift and Data Drift Tracking."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.drift.schema_drift import SchemaDriftTracker
from app.drift.data_drift import DataDriftEngine
from app.database.registry import connection_registry
from app.discovery.schema import SchemaDiscoverer

router = APIRouter(prefix="/api/drift", tags=["Data & Schema Drift"])


class SnapshotRequest(BaseModel):
    database_name: str
    table_name: Optional[str] = None


@router.post("/snapshot")
def take_drift_snapshot(req: SnapshotRequest):
    """Takes a schema snapshot and updates baseline statistics for data drift tracking."""
    conn = connection_registry.get_connection(req.database_name)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Database '{req.database_name}' not found.")

    s_tracker = SchemaDriftTracker(req.database_name)
    schema_snaps = s_tracker.take_snapshot()

    d_engine = DataDriftEngine(req.database_name)
    disc = SchemaDiscoverer(req.database_name)
    cat = disc.discover_catalog()
    table_names = [req.table_name] if req.table_name else [t["name"] for t in cat.get("tables", [])]

    data_baselines = {}
    for t_name in table_names:
        try:
            data_baselines[t_name] = d_engine.save_baseline_snapshot(t_name)
        except Exception:
            pass

    return {
        "success": True,
        "database_name": req.database_name,
        "schema_snapshots_count": len(schema_snaps),
        "data_baselines_count": sum(len(v) for v in data_baselines.values()),
    }


@router.get("/schema/{database_name}")
def get_schema_drift(database_name: str):
    """Evaluates schema differences against historical baseline (added, removed, type-mutated columns)."""
    conn = connection_registry.get_connection(database_name)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Database '{database_name}' not found.")

    tracker = SchemaDriftTracker(database_name)
    return tracker.detect_schema_drift()


@router.get("/data/{database_name}")
def get_data_drift(database_name: str, table: Optional[str] = Query(None)):
    """Runs Kolmogorov-Smirnov test and statistical divergence analysis on numerical columns."""
    conn = connection_registry.get_connection(database_name)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Database '{database_name}' not found.")

    d_engine = DataDriftEngine(database_name)
    disc = SchemaDiscoverer(database_name)
    cat = disc.discover_catalog()
    all_tables = [t["name"] for t in cat.get("tables", [])]

    target_tables = [table] if table and table in all_tables else all_tables

    tables_drift = []
    total_drifted_cols = 0
    for t_name in target_tables:
        try:
            res = d_engine.detect_data_drift(t_name)
            tables_drift.append(res)
            total_drifted_cols += res.get("drifted_columns_count", 0)
        except Exception as e:
            tables_drift.append({
                "database_name": database_name,
                "table_name": t_name,
                "status": "ERROR",
                "error": str(e),
            })

    return {
        "database_name": database_name,
        "total_tables_analyzed": len(tables_drift),
        "total_drifted_columns": total_drifted_cols,
        "overall_status": "DRIFT_DETECTED" if total_drifted_cols > 0 else "STABLE",
        "tables": tables_drift,
    }
