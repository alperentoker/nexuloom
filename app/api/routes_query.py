import time
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.core.audit import audit_logger
from app.core.cache import cache
from app.core.lineage import lineage_tracker
from app.database.registry import connection_registry
from app.database.connection import db_manager
from app.database.safety import SQLSafetyValidator, SQLSafetyError
from app.discovery.schema import SchemaDiscoverer
from app.llm.client import llm_client

router = APIRouter(prefix="/api/query", tags=["SQL & NL Analysis"])


class DirectSQLRequest(BaseModel):
    database_name: str
    sql: str
    limit: Optional[int] = 1000


class NaturalLanguageQueryRequest(BaseModel):
    database_name: str
    question: str


@router.post("/execute")
def execute_sql(req: DirectSQLRequest):
    t0 = time.time()
    try:
        engine = connection_registry.get_engine_for(req.database_name)
        df = db_manager.execute_read_only_df(
            engine=engine,
            sql_query=req.sql,
            max_rows=req.limit or 1000,
            enforce_limit=True,
        )
        elapsed_ms = round((time.time() - t0) * 1000, 2)

        records = df.to_dict(orient="records")
        columns = list(df.columns)

        audit_logger.log(
            action="QUERY_EXECUTE",
            database_name=req.database_name,
            query_text=req.sql,
            execution_time_ms=elapsed_ms,
            details={"rows": len(records)},
        )

        return {
            "database_name": req.database_name,
            "sql": req.sql,
            "row_count": len(records),
            "execution_time_ms": elapsed_ms,
            "columns": columns,
            "data": records,
        }
    except SQLSafetyError as se:
        audit_logger.log(
            action="QUERY_SAFETY_BLOCKED",
            status="BLOCKED",
            database_name=req.database_name,
            query_text=req.sql,
            details={"error": str(se)},
        )
        raise HTTPException(status_code=403, detail=f"SQL Safety Violation: {str(se)}")
    except Exception as e:
        audit_logger.log(
            action="QUERY_EXECUTE",
            status="ERROR",
            database_name=req.database_name,
            query_text=req.sql,
            details={"error": str(e)},
        )
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/natural-language")
def ask_natural_language(req: NaturalLanguageQueryRequest):
    try:
        discoverer = SchemaDiscoverer(req.database_name)
        catalog = discoverer.discover_catalog()

        sql_query, explanation, is_llm = llm_client.generate_sql_from_nl(req.question, catalog)

        # Execute safe SQL
        t0 = time.time()
        engine = connection_registry.get_engine_for(req.database_name)
        df = db_manager.execute_read_only_df(
            engine=engine,
            sql_query=sql_query,
            max_rows=1000,
            enforce_limit=True,
        )
        elapsed_ms = round((time.time() - t0) * 1000, 2)

        records = df.to_dict(orient="records")
        columns = list(df.columns)

        # Record lineage
        lineage_tracker.record(
            item_type="NL_QUERY",
            item_id=f"NLQ:{hash(req.question) % 1000000}",
            item_label=req.question,
            source_db=req.database_name,
            source_query=sql_query,
            metadata={"row_count": len(records), "is_llm": is_llm},
        )

        return {
            "question": req.question,
            "generated_sql": sql_query,
            "explanation": explanation,
            "is_llm_used": is_llm,
            "execution_time_ms": elapsed_ms,
            "row_count": len(records),
            "columns": columns,
            "data": records,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
