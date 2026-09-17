import pytest
from app.database.safety import SQLSafetyValidator, SQLSafetyError
from app.core.security import mask_secret, mask_connection_url, mask_dict_secrets
from app.database.registry import connection_registry


def test_sql_safety_blocks_destructive_queries():
    dangerous_queries = [
        "DROP TABLE users;",
        "DELETE FROM orders WHERE id = 1",
        "UPDATE employees SET salary = 999999",
        "INSERT INTO customers (id, name) VALUES (1, 'Hacker')",
        "TRUNCATE TABLE production",
        "ALTER TABLE products ADD COLUMN secret TEXT",
        "SELECT * FROM orders; DROP TABLE orders;",
        "CREATE TABLE backdoors (id INT)",
        "GRANT ALL PRIVILEGES ON *.* TO 'user'@'%'",
    ]

    for q in dangerous_queries:
        is_valid, err = SQLSafetyValidator.validate_read_only(q)
        assert not is_valid, f"Expected query '{q}' to be blocked, but it was marked valid."


def test_sql_safety_allows_read_only_queries():
    valid_queries = [
        "SELECT * FROM orders",
        "SELECT id, name, SUM(amount) FROM sales GROUP BY id, name",
        "WITH monthly_sales AS (SELECT date, amount FROM orders) SELECT * FROM monthly_sales",
        "SELECT * FROM products WHERE price > 100 ORDER BY price DESC LIMIT 50;",
        "EXPLAIN SELECT * FROM inventory",
    ]

    for q in valid_queries:
        is_valid, err = SQLSafetyValidator.validate_read_only(q)
        assert is_valid, f"Expected query '{q}' to be valid, but got error: {err}"


def test_sql_safety_enforces_limit():
    q = "SELECT * FROM orders"
    limited = SQLSafetyValidator.enforce_safety_and_limit(q, max_rows=50000, default_limit=1000)
    assert "LIMIT 1000" in limited

    # Replaces higher limits
    q_high = "SELECT * FROM orders LIMIT 100000"
    enforced = SQLSafetyValidator.enforce_safety_and_limit(q_high, max_rows=50000)
    assert "LIMIT 50000" in enforced


def test_secret_masking():
    raw_url = "postgresql://analyst:SuperSecretP@ss123@localhost:5432/production_db"
    masked = mask_connection_url(raw_url)
    assert "SuperSecretP@ss123" not in masked
    assert "analyst:****@" in masked

    data = {
        "username": "analyst",
        "password": "my_db_password",
        "connection_url": raw_url,
        "nested": {"token": "secret_token_value", "metric": 42},
    }
    sanitized = mask_dict_secrets(data)
    assert sanitized["password"] == "********"
    assert "my_db_password" not in str(sanitized)
    assert "secret_token_value" not in str(sanitized)
    assert sanitized["nested"]["metric"] == 42


def test_database_registry():
    conns = connection_registry.list_connections()
    assert isinstance(conns, list)
    assert any(c["name"] == "demo_enterprise" for c in conns)
