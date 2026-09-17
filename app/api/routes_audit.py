from typing import Optional
from fastapi import APIRouter, Query
from app.core.audit import audit_logger
from app.core.lineage import lineage_tracker

router = APIRouter(prefix="/api/audit", tags=["Audit & Lineage"])


@router.get("/logs")
def get_audit_logs(
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    action: Optional[str] = Query(None),
    database_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
):
    logs = audit_logger.list_logs(
        limit=limit,
        offset=offset,
        action=action,
        database_name=database_name,
        status=status,
    )
    total = audit_logger.count_logs()
    return {"total": total, "limit": limit, "offset": offset, "logs": logs}


@router.get("/lineage/graph")
def get_lineage_graph(limit: int = Query(100, le=500)):
    return lineage_tracker.get_full_graph(limit=limit)


@router.get("/lineage/chain/{item_id}")
def get_lineage_chain(item_id: str):
    return lineage_tracker.get_lineage_chain(item_id)
