from typing import Any, Dict, List, Optional
from sqlalchemy import inspect, text, select, func, table as sa_table
from sqlalchemy.engine import Engine
from app.database.registry import connection_registry
from app.database.safety import SQLSafetyValidator
from app.core.audit import audit_logger
from app.core.cache import cache


class SchemaDiscoverer:
    """Discovers database catalog, tables, columns, constraints, and row counts."""

    def __init__(self, db_name: str, engine: Optional[Engine] = None):
        self.db_name = db_name
        self.engine = engine or connection_registry.get_engine_for(db_name)

    def discover_catalog(self, use_cache: bool = True) -> Dict[str, Any]:
        """Discovers the complete schema catalog of the connected database."""
        cache_key = cache.generate_key("schema_catalog", self.db_name)
        if use_cache:
            cached = cache.get(cache_key)
            if cached:
                return cached

        inspector = inspect(self.engine)
        schemas = inspector.get_schema_names() if hasattr(inspector, "get_schema_names") else [None]
        if not schemas:
            schemas = [None]

        tables_data = []
        total_rows = 0

        # SQLite often has schema=None or 'main'
        for schema in schemas:
            if schema in ("information_schema", "pg_catalog", "sys"):
                continue

            try:
                table_names = list(inspector.get_table_names(schema=schema))
                if hasattr(inspector, "get_view_names"):
                    try:
                        for vn in inspector.get_view_names(schema=schema):
                            if vn not in table_names:
                                table_names.append(vn)
                    except Exception:
                        pass
            except Exception:
                table_names = []

            for tbl in table_names:
                table_info = self.inspect_table(tbl, schema=schema, inspector=inspector)
                tables_data.append(table_info)
                total_rows += table_info.get("row_count", 0)

        catalog = {
            "database_name": self.db_name,
            "schemas": [s for s in schemas if s],
            "table_count": len(tables_data),
            "total_rows": total_rows,
            "tables": tables_data,
        }

        # Cache catalog for 1 hour
        cache.set(cache_key, catalog, ttl_seconds=3600, database_name=self.db_name)
        audit_logger.log(
            action="SCHEMA_DISCOVERY",
            database_name=self.db_name,
            details={"table_count": len(tables_data), "total_rows": total_rows},
        )
        return catalog

    def inspect_table(
        self,
        table_name: str,
        schema: Optional[str] = None,
        inspector: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Inspects a single table's columns, keys, indexes, and row count."""
        insp = inspector or inspect(self.engine)

        columns_data = []
        try:
            cols = insp.get_columns(table_name, schema=schema)
        except Exception:
            cols = []

        try:
            pk_constraint = insp.get_pk_constraint(table_name, schema=schema)
            pk_cols = set(pk_constraint.get("constrained_columns", []))
        except Exception:
            pk_cols = set()

        try:
            foreign_keys = insp.get_foreign_keys(table_name, schema=schema)
        except Exception:
            foreign_keys = []

        fk_map = {}
        for fk in foreign_keys:
            for c_col, r_col in zip(fk.get("constrained_columns", []), fk.get("referred_columns", [])):
                fk_map[c_col] = {
                    "referred_table": fk.get("referred_table"),
                    "referred_schema": fk.get("referred_schema"),
                    "referred_column": r_col,
                }

        try:
            indexes = insp.get_indexes(table_name, schema=schema)
        except Exception:
            indexes = []

        indexed_cols = {col for idx in indexes for col in idx.get("column_names", []) if col}
        unique_indexes = {
            col for idx in indexes if idx.get("unique") for col in idx.get("column_names", []) if col
        }

        for c in cols:
            c_name = c["name"]
            c_type = str(c["type"])
            is_pk = c_name in pk_cols
            is_fk = c_name in fk_map
            is_unique = is_pk or (c_name in unique_indexes)

            columns_data.append({
                "name": c_name,
                "type": c_type,
                "nullable": c.get("nullable", True),
                "primary_key": is_pk,
                "foreign_key": fk_map.get(c_name),
                "unique": is_unique,
                "indexed": c_name in indexed_cols or is_pk,
                "default": str(c.get("default", "")) if c.get("default") is not None else None,
            })

        # Calculate row count safely (dialect-agnostic and SQL-safe)
        row_count = 0
        try:
            safe_tbl = SQLSafetyValidator.validate_identifier(table_name)
            safe_schema = SQLSafetyValidator.validate_identifier(schema) if schema else None
            tbl_clause = sa_table(safe_tbl, schema=safe_schema)
            stmt = select(func.count()).select_from(tbl_clause)
            with self.engine.connect() as conn:
                res = conn.execute(stmt).scalar()
                row_count = int(res) if res is not None else 0
        except Exception:
            row_count = 0

        return {
            "name": table_name,
            "schema": schema,
            "column_count": len(columns_data),
            "row_count": row_count,
            "columns": columns_data,
            "primary_keys": list(pk_cols),
            "foreign_keys": foreign_keys,
            "indexes": indexes,
        }
