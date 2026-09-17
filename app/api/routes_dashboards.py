"""FastAPI routes for Custom BI Dashboards and Widgets."""

from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.dashboards.manager import custom_dashboard_manager
from app.database.safety import SQLSafetyError

router = APIRouter(prefix="/api/dashboards", tags=["Custom Dashboards"])


class CreateDashboardRequest(BaseModel):
    title: str = Field(..., description="Dashboard title")
    description: Optional[str] = Field("", description="Optional dashboard description")


class AddWidgetRequest(BaseModel):
    title: str = Field(..., description="Widget title")
    widget_type: str = Field(..., description="kpi_card, bar_chart, line_chart, donut_chart, table")
    database_name: str = Field(..., description="Target database name")
    sql_query: str = Field(..., description="Safe read-only SQL query")
    grid_w: Optional[int] = Field(6, description="Grid column width (1-12)")
    grid_h: Optional[int] = Field(4, description="Grid row height")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


class UpdateWidgetRequest(BaseModel):
    title: Optional[str] = None
    widget_type: Optional[str] = None
    database_name: Optional[str] = None
    sql_query: Optional[str] = None
    grid_x: Optional[int] = None
    grid_y: Optional[int] = None
    grid_w: Optional[int] = None
    grid_h: Optional[int] = None
    config: Optional[Dict[str, Any]] = None


class PreviewWidgetRequest(BaseModel):
    database_name: str
    sql_query: str
    widget_type: str
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)


@router.get("")
def list_dashboards():
    """Lists all user-created and default custom dashboards."""
    return {"dashboards": custom_dashboard_manager.list_dashboards()}


@router.post("")
def create_dashboard(req: CreateDashboardRequest):
    """Creates a new custom BI dashboard."""
    d = custom_dashboard_manager.create_dashboard(req.title, req.description)
    return {"success": True, "dashboard": d}


@router.get("/{dashboard_id}")
def get_dashboard(dashboard_id: str):
    """Retrieves a custom dashboard along with its configured widgets."""
    d = custom_dashboard_manager.get_dashboard(dashboard_id)
    if not d:
        raise HTTPException(status_code=404, detail=f"Dashboard '{dashboard_id}' not found.")
    return d


@router.put("/{dashboard_id}")
def update_dashboard(dashboard_id: str, req: CreateDashboardRequest):
    """Updates dashboard title and description."""
    d = custom_dashboard_manager.update_dashboard(dashboard_id, req.title, req.description)
    if not d:
        raise HTTPException(status_code=404, detail=f"Dashboard '{dashboard_id}' not found.")
    return {"success": True, "dashboard": d}


@router.delete("/{dashboard_id}")
def delete_dashboard(dashboard_id: str):
    """Deletes a custom dashboard and all its widgets."""
    success = custom_dashboard_manager.delete_dashboard(dashboard_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Dashboard '{dashboard_id}' not found.")
    return {"success": True, "message": "Dashboard deleted."}


@router.post("/{dashboard_id}/widgets")
def add_widget(dashboard_id: str, req: AddWidgetRequest):
    """Adds a new query-driven widget to the dashboard."""
    d = custom_dashboard_manager.get_dashboard(dashboard_id)
    if not d:
        raise HTTPException(status_code=404, detail=f"Dashboard '{dashboard_id}' not found.")

    try:
        w = custom_dashboard_manager.add_widget(
            dashboard_id=dashboard_id,
            title=req.title,
            widget_type=req.widget_type,
            database_name=req.database_name,
            sql_query=req.sql_query,
            grid_w=req.grid_w or 6,
            grid_h=req.grid_h or 4,
            config=req.config or {},
        )
        return {"success": True, "widget": w}
    except SQLSafetyError as se:
        raise HTTPException(status_code=403, detail=f"SQL Safety Error: {str(se)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{dashboard_id}/widgets/{widget_id}")
def update_widget(dashboard_id: str, widget_id: str, req: UpdateWidgetRequest):
    """Updates a widget's position, dimensions, query, or display config."""
    try:
        w = custom_dashboard_manager.update_widget(
            widget_id=widget_id,
            title=req.title,
            widget_type=req.widget_type,
            database_name=req.database_name,
            sql_query=req.sql_query,
            grid_x=req.grid_x,
            grid_y=req.grid_y,
            grid_w=req.grid_w,
            grid_h=req.grid_h,
            config=req.config,
        )
        if not w:
            raise HTTPException(status_code=404, detail=f"Widget '{widget_id}' not found.")
        return {"success": True, "widget": w}
    except SQLSafetyError as se:
        raise HTTPException(status_code=403, detail=f"SQL Safety Error: {str(se)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{dashboard_id}/widgets/{widget_id}")
def delete_widget(dashboard_id: str, widget_id: str):
    """Removes a widget from the dashboard."""
    success = custom_dashboard_manager.delete_widget(widget_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Widget '{widget_id}' not found.")
    return {"success": True, "message": "Widget removed."}


@router.get("/{dashboard_id}/widgets/{widget_id}/data")
def get_widget_live_data(dashboard_id: str, widget_id: str):
    """Executes the widget SQL query safely and returns live chart/metric data."""
    w = custom_dashboard_manager.get_widget(widget_id)
    if not w:
        raise HTTPException(status_code=404, detail=f"Widget '{widget_id}' not found.")

    try:
        data = custom_dashboard_manager.execute_widget_data(w)
        return data
    except SQLSafetyError as se:
        raise HTTPException(status_code=403, detail=f"SQL Safety Error: {str(se)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/preview-widget")
def preview_widget_data(req: PreviewWidgetRequest):
    """Previews live query execution and formatting before saving as widget."""
    try:
        dummy_widget = {
            "id": "preview",
            "title": "Preview",
            "widget_type": req.widget_type,
            "database_name": req.database_name,
            "sql_query": req.sql_query,
            "config": req.config or {},
        }
        data = custom_dashboard_manager.execute_widget_data(dummy_widget)
        return {"success": True, "preview": data}
    except SQLSafetyError as se:
        raise HTTPException(status_code=403, detail=f"SQL Safety Error: {str(se)}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
