from fastapi import APIRouter, HTTPException, Query
from app.profiling.profiler import DataProfiler

router = APIRouter(prefix="/api/profiling", tags=["Data Profiling"])


@router.get("/{db_name}/{table_name}")
def profile_table(
    db_name: str,
    table_name: str,
    sample_size: int = Query(50000, le=200000),
    refresh: bool = Query(False),
):
    try:
        profiler = DataProfiler(db_name)
        result = profiler.profile_table(
            table_name=table_name,
            sample_size=sample_size,
            use_cache=not refresh,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
