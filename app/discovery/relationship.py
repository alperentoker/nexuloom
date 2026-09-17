from typing import Any, Dict, List, Set, Tuple
from app.discovery.schema import SchemaDiscoverer


class RelationshipDiscoverer:
    """Discovers explicit foreign key relationships and infers implicit relationships."""

    def __init__(self, discoverer: SchemaDiscoverer):
        self.discoverer = discoverer

    def discover_relationships(self) -> Dict[str, Any]:
        """Builds an Entity-Relationship (ER) graph with nodes and relationship edges."""
        catalog = self.discoverer.discover_catalog()
        tables = catalog.get("tables", [])

        nodes = []
        edges = []
        seen_edges: Set[Tuple[str, str, str, str]] = set()

        table_map = {t["name"]: t for t in tables}

        # 1. Add table nodes
        for t in tables:
            nodes.append({
                "id": t["name"],
                "label": t["name"],
                "row_count": t.get("row_count", 0),
                "column_count": t.get("column_count", 0),
                "columns": [c["name"] for c in t.get("columns", [])],
                "primary_keys": t.get("primary_keys", []),
            })

        # 2. Extract explicit foreign keys
        for t in tables:
            source_table = t["name"]
            for fk in t.get("foreign_keys", []):
                target_table = fk.get("referred_table")
                if not target_table or target_table not in table_map:
                    continue

                for c_col, r_col in zip(fk.get("constrained_columns", []), fk.get("referred_columns", [])):
                    edge_key = (source_table, c_col, target_table, r_col)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        edges.append({
                            "source": source_table,
                            "source_column": c_col,
                            "target": target_table,
                            "target_column": r_col,
                            "relationship_type": "EXPLICIT_FK",
                            "label": f"{source_table}.{c_col} → {target_table}.{r_col}",
                        })

        # 3. Heuristic relationship discovery (inferred relationships)
        # Naming patterns: {entity}_id, {entity}_code, id_{entity}
        for t in tables:
            source_table = t["name"]
            for col in t.get("columns", []):
                col_name = col["name"].lower()
                if col["primary_key"]:
                    continue

                # Check if it ends with _id or _code
                inferred_target = None
                inferred_target_col = "id"

                if col_name.endswith("_id"):
                    prefix = col_name[:-3]
                    # Check plural or direct match
                    candidates = [
                        prefix,
                        f"{prefix}s",
                        f"{prefix}es",
                        f"{prefix[:-1]}ies" if prefix.endswith("y") else None,
                    ]
                    for cand in candidates:
                        if cand and cand in table_map and cand != source_table:
                            # Verify candidate has PK 'id' or prefix + '_id'
                            cand_pks = [p.lower() for p in table_map[cand].get("primary_keys", [])]
                            if "id" in cand_pks:
                                inferred_target = cand
                                inferred_target_col = "id"
                                break
                            elif col_name in cand_pks:
                                inferred_target = cand
                                inferred_target_col = col["name"]
                                break

                if inferred_target:
                    edge_key = (source_table, col["name"], inferred_target, inferred_target_col)
                    if edge_key not in seen_edges:
                        seen_edges.add(edge_key)
                        edges.append({
                            "source": source_table,
                            "source_column": col["name"],
                            "target": inferred_target,
                            "target_column": inferred_target_col,
                            "relationship_type": "INFERRED_FK",
                            "label": f"{source_table}.{col['name']} ⤏ {inferred_target}.{inferred_target_col} (inferred)",
                        })

        # 4. Generate structured hierarchy tree representation for top root entities
        # A root entity has incoming relationships or high row count with 0 outgoing FKs
        root_nodes = [n["id"] for n in nodes if not any(e["source"] == n["id"] for e in edges)]
        if not root_nodes and nodes:
            root_nodes = [nodes[0]["id"]]

        return {
            "database_name": self.discoverer.db_name,
            "nodes": nodes,
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "root_entities": root_nodes,
        }
