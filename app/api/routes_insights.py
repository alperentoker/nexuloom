from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.insights.insight_engine import InsightEngine
from app.insights.root_cause import RootCauseTreeBuilder

router = APIRouter(prefix="/api/insights", tags=["Insights & Root Cause"])


class VarianceAnalysisRequest(BaseModel):
    database_name: str
    table_name: str
    metric_column: str
    date_column: str
    dimension_columns: Optional[List[str]] = None
    period_split_date: Optional[str] = None


class RootCauseTreeRequest(BaseModel):
    database_name: str
    table_name: str
    metric_column: str
    date_column: str
    dimension_hierarchy: List[str]


@router.post("/variance")
def analyze_metric_variance(req: VarianceAnalysisRequest):
    try:
        engine = InsightEngine(req.database_name)
        return engine.analyze_metric_variance(
            table_name=req.table_name,
            metric_col=req.metric_column,
            date_col=req.date_column,
            dimension_cols=req.dimension_columns,
            period_split_date=req.period_split_date,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/root-cause-tree")
def build_root_cause_tree(req: RootCauseTreeRequest):
    try:
        builder = RootCauseTreeBuilder(req.database_name)
        return builder.build_drill_down_tree(
            table_name=req.table_name,
            metric_col=req.metric_column,
            date_col=req.date_column,
            dimension_hierarchy=req.dimension_hierarchy,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
