import pytest
from app.discovery.schema import SchemaDiscoverer
from app.discovery.relationship import RelationshipDiscoverer


def test_schema_discovery():
    discoverer = SchemaDiscoverer("demo_enterprise")
    catalog = discoverer.discover_catalog()

    assert catalog["database_name"] == "demo_enterprise"
    assert catalog["table_count"] >= 11
    assert catalog["total_rows"] > 50000

    table_names = [t["name"] for t in catalog["tables"]]
    expected = ["orders", "products", "customers", "employees", "companies", "inventory", "production", "machines", "maintenance", "expenses"]
    for exp in expected:
        assert exp in table_names


def test_table_inspection():
    discoverer = SchemaDiscoverer("demo_enterprise")
    orders_info = discoverer.inspect_table("orders")

    assert orders_info["name"] == "orders"
    assert orders_info["row_count"] >= 20000
    col_names = [c["name"] for c in orders_info["columns"]]
    assert "id" in col_names
    assert "customer_id" in col_names
    assert "total_amount" in col_names
    assert "order_date" in col_names


def test_relationship_discovery():
    discoverer = SchemaDiscoverer("demo_enterprise")
    rel_discoverer = RelationshipDiscoverer(discoverer)
    rels = rel_discoverer.discover_relationships()

    assert rels["total_nodes"] >= 11
    assert rels["total_edges"] > 0

    # Verify orders -> customers relationship is captured
    found_order_cust = any(
        e["source"] == "orders" and e["target"] == "customers" for e in rels["edges"]
    )
    assert found_order_cust, "Expected orders -> customers foreign key relationship."
