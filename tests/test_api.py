import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_api_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "HEALTHY"


def test_api_databases():
    resp = client.get("/api/databases")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert any(d["name"] == "demo_enterprise" for d in data)


def test_api_catalog():
    resp = client.get("/api/discovery/catalog/demo_enterprise")
    assert resp.status_code == 200
    data = resp.json()
    assert data["table_count"] >= 11


def test_api_profiling():
    resp = client.get("/api/profiling/demo_enterprise/orders?sample_size=1000")
    assert resp.status_code == 200
    data = resp.json()
    assert data["table_name"] == "orders"
    assert "columns" in data


def test_api_quality():
    resp = client.get("/api/quality/demo_enterprise?sample_size=1000")
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_quality_score" in data


def test_api_kpis():
    resp = client.get("/api/kpis?database_name=demo_enterprise")
    assert resp.status_code == 200
    kpis = resp.json()
    assert len(kpis) > 0


def test_api_query_safe_and_blocked():
    # 1. Safe query
    resp = client.post(
        "/api/query/execute",
        json={"database_name": "demo_enterprise", "sql": "SELECT id, total_amount FROM orders LIMIT 5"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["row_count"] == 5

    # 2. Blocked destructive query
    bad_resp = client.post(
        "/api/query/execute",
        json={"database_name": "demo_enterprise", "sql": "DROP TABLE orders;"},
    )
    assert bad_resp.status_code == 403
    assert "Safety Violation" in bad_resp.json()["detail"]


def test_api_audit_logs():
    resp = client.get("/api/audit/logs?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "logs" in data


def test_api_root_and_favicons():
    # Verify root endpoint supports both GET and HEAD
    get_root = client.get("/")
    assert get_root.status_code == 200

    head_root = client.head("/")
    assert head_root.status_code == 200

    # Verify /favicon.ico supports GET and HEAD
    get_fav = client.get("/favicon.ico")
    assert get_fav.status_code == 200
    assert get_fav.headers.get("content-type") == "image/x-icon"

    head_fav = client.head("/favicon.ico")
    assert head_fav.status_code == 200
    assert head_fav.headers.get("content-type") == "image/x-icon"

    # Verify PNG and Apple Touch icons
    head_apple = client.head("/apple-touch-icon.png")
    assert head_apple.status_code == 200
    assert head_apple.headers.get("content-type") == "image/png"

