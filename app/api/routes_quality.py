from fastapi import APIRouter, HTTPException, Query
from app.quality.engine import DataQualityEngine

router = APIRouter(prefix="/api/quality", tags=["Data Quality"])


@router.get("/{db_name}")
def get_database_quality(
    db_name: str,
    sample_size: int = Query(25000, le=100000),
    refresh: bool = Query(False),
):
    try:
        engine = DataQualityEngine(db_name)
        return engine.evaluate_database(sample_size=sample_size, use_cache=not refresh)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{db_name}/{table_name}")
def get_table_quality(
    db_name: str,
    table_name: str,
    sample_size: int = Query(50000, le=100000),
):
    try:
        engine = DataQualityEngine(db_name)
        return engine.evaluate_table(table_name=table_name, sample_size=sample_size)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
