import pytest
from app.database.duckdb_connector import duckdb_manager
from app.database.safety import SQLSafetyError


def test_duckdb_auto_register_and_tables():
    registered = duckdb_manager.auto_register_workspace_files()
    assert isinstance(registered, list)

    tables = duckdb_manager.get_tables()
    table_names = [t["name"] for t in tables]
    assert "sales_analytics" in table_names or "sales" in table_names


def test_duckdb_query_execution():
    df = duckdb_manager.execute_read_only_df("SELECT * FROM sales_analytics LIMIT 5")
    assert not df.empty
    assert len(df) <= 5
    assert "amount" in df.columns


def test_duckdb_safety_block_modifications():
    with pytest.raises(SQLSafetyError):
        duckdb_manager.execute_read_only_df("DROP VIEW sales_analytics")

    with pytest.raises(SQLSafetyError):
        duckdb_manager.execute_read_only_df("DELETE FROM sales_analytics WHERE 1=1")
