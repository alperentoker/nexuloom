from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from app.anomaly.detector import AnomalyEngine

router = APIRouter(prefix="/api/anomalies", tags=["Anomaly Detection"])


@router.get("/{db_name}/{table_name}")
def scan_table_anomalies(
    db_name: str,
    table_name: str,
    metric_column: str = Query(...),
    entity_column: Optional[str] = Query(None),
    method: str = Query("ALL"),  # ZSCORE, IQR, ROLLING, ISOLATION_FOREST, ALL
    limit: int = Query(25000, le=100000),
):
    try:
        engine = AnomalyEngine(db_name)
        return engine.scan_table(
            table_name=table_name,
            metric_col=metric_column,
            entity_col=entity_column,
            method=method,
            limit=limit,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
