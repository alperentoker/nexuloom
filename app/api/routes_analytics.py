from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.analytics.trends import TrendAnalyzer
from app.metrics.kpi_engine import kpi_engine

router = APIRouter(prefix="/api/analytics", tags=["Analytics & Trends"])


class TrendAnalysisRequest(BaseModel):
    metric_name: str
    unit: Optional[str] = ""
    data_points: List[Dict[str, Any]]


@router.post("/trends")
def analyze_trends(req: TrendAnalysisRequest):
    try:
        res = TrendAnalyzer.analyze_series(
            data_points=req.data_points,
            metric_name=req.metric_name,
            unit=req.unit or "",
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/kpi-trend/{kpi_name}")
def analyze_kpi_trend(kpi_name: str):
    try:
        k_eval = kpi_engine.evaluate_kpi(kpi_name)
        ts = k_eval.get("time_series", [])
        return TrendAnalyzer.analyze_series(
            data_points=ts,
            metric_name=kpi_name,
            unit=k_eval.get("unit", ""),
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
