from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.metrics.kpi_engine import kpi_engine

router = APIRouter(prefix="/api/kpis", tags=["KPI Engine"])


class KPICreateRequest(BaseModel):
    name: str
    database_name: str
    table_name: str
    formula: str
    description: Optional[str] = ""
    date_column: Optional[str] = None
    target_value: Optional[float] = None
    unit: Optional[str] = ""
    higher_is_better: bool = True


@router.get("")
def list_kpis(database_name: Optional[str] = Query(None)):
    return kpi_engine.list_kpis(database_name=database_name)


@router.post("")
def add_kpi(req: KPICreateRequest):
    try:
        res = kpi_engine.add_kpi(
            name=req.name,
            database_name=req.database_name,
            table_name=req.table_name,
            formula=req.formula,
            description=req.description or "",
            date_column=req.date_column,
            target_value=req.target_value,
            unit=req.unit or "",
            higher_is_better=req.higher_is_better,
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{name}/evaluate")
def evaluate_kpi(name: str):
    try:
        return kpi_engine.evaluate_kpi(name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{name}")
def delete_kpi(name: str):
    success = kpi_engine.delete_kpi(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"KPI '{name}' not found.")
    return {"success": True, "message": f"KPI '{name}' deleted."}
