from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from app.rules.rule_engine import business_rule_engine

router = APIRouter(prefix="/api/rules", tags=["Business Rules"])


class RuleCreateRequest(BaseModel):
    name: str
    database_name: str
    table_name: str
    condition_sql: str
    severity: str = "HIGH"
    alert_message: str = "Business condition violated."


class ToggleRuleRequest(BaseModel):
    is_active: bool


@router.get("")
def list_rules(database_name: Optional[str] = Query(None)):
    return business_rule_engine.list_rules(database_name=database_name)


@router.post("")
def create_rule(req: RuleCreateRequest):
    try:
        return business_rule_engine.create_rule(
            name=req.name,
            database_name=req.database_name,
            table_name=req.table_name,
            condition_sql=req.condition_sql,
            severity=req.severity,
            alert_message=req.alert_message,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{name}/execute")
def execute_rule(name: str):
    try:
        return business_rule_engine.execute_rule(name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{name}/toggle")
def toggle_rule(name: str, req: ToggleRuleRequest):
    success = business_rule_engine.toggle_rule(name, req.is_active)
    if not success:
        raise HTTPException(status_code=404, detail=f"Rule '{name}' not found.")
    return {"success": True, "is_active": req.is_active}


@router.post("/execute-all")
def execute_all_rules(database_name: Optional[str] = Query(None)):
    return business_rule_engine.execute_all_rules(database_name=database_name)


@router.delete("/{name}")
def delete_rule(name: str):
    success = business_rule_engine.delete_rule(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Rule '{name}' not found.")
    return {"success": True, "message": f"Rule '{name}' deleted."}
