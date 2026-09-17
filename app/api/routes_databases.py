from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database.registry import connection_registry
from app.database.connection import db_manager
from app.core.audit import audit_logger

router = APIRouter(prefix="/api/databases", tags=["Databases"])


class ConnectionCreateRequest(BaseModel):
    name: str
    db_type: str  # sqlite, postgresql, mysql, mssql
    database_name: str
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    raw_url: Optional[str] = None


@router.get("")
def list_databases():
    return connection_registry.list_connections()


@router.post("/auto-discover")
def auto_discover_databases():
    """Scans workspace for any existing SQLite databases and registers them."""
    discovered = connection_registry.auto_discover_local_sqlite()
    all_conns = connection_registry.list_connections()
    return {"discovered": discovered, "all_connections": all_conns}


@router.post("")
def add_database(req: ConnectionCreateRequest):
    try:
        res = connection_registry.add_connection(
            name=req.name,
            db_type=req.db_type,
            database_name=req.database_name,
            host=req.host,
            port=req.port,
            username=req.username,
            password=req.password,
            raw_url=req.raw_url,
        )
        test_result = connection_registry.test_and_update_status(req.name)
        res["test_status"] = test_result
        audit_logger.log(
            action="DATABASE_CREATE",
            database_name=req.name,
            details={"type": req.db_type, "status": test_result.get("status")},
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{name}")
def get_database(name: str):
    info = connection_registry.get_connection(name, include_secrets=False)
    if not info:
        raise HTTPException(status_code=404, detail=f"Database '{name}' not found.")
    return info


@router.post("/{name}/test")
def test_database(name: str):
    res = connection_registry.test_and_update_status(name)
    return res


@router.delete("/{name}")
def delete_database(name: str):
    success = connection_registry.delete_connection(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Database '{name}' not found.")
    audit_logger.log(action="DATABASE_DELETE", database_name=name)
    return {"success": True, "message": f"Connection '{name}' deleted."}
