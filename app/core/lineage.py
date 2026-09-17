import sqlite3
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.core.config import settings


class LineageTracker:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = str(db_path or settings.SYSTEM_DB_PATH)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS lineage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    item_type TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    item_label TEXT NOT NULL,
                    source_db TEXT,
                    source_table TEXT,
                    source_query TEXT,
                    parent_id TEXT,
                    metadata_json TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lineage_item ON lineage_records(item_type, item_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_lineage_parent ON lineage_records(parent_id)")
            conn.commit()

    def record(
        self,
        item_type: str,
        item_id: str,
        item_label: str,
        source_db: Optional[str] = None,
        source_table: Optional[str] = None,
        source_query: Optional[str] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        now = datetime.now(timezone.utc).isoformat()
        metadata_str = json.dumps(metadata or {}, default=str)
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO lineage_records (
                    item_type, item_id, item_label, source_db, source_table,
                    source_query, parent_id, metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (item_type, item_id, item_label, source_db, source_table, source_query, parent_id, metadata_str, now),
            )
            conn.commit()
            return cursor.lastrowid

    def get_lineage_chain(self, item_id: str) -> List[Dict[str, Any]]:
        """Traverses backwards from an item up to its original root database/table."""
        chain = []
        curr_id = item_id
        visited = set()

        with self._get_connection() as conn:
            while curr_id and curr_id not in visited:
                visited.add(curr_id)
                row = conn.execute(
                    "SELECT * FROM lineage_records WHERE item_id = ? ORDER BY id DESC LIMIT 1",
                    (curr_id,),
                ).fetchone()
                if not row:
                    break
                item = dict(row)
                if item.get("metadata_json"):
                    try:
                        item["metadata"] = json.loads(item["metadata_json"])
                    except Exception:
                        item["metadata"] = {}
                chain.append(item)
                curr_id = item.get("parent_id")

        return chain

    def get_full_graph(self, limit: int = 100) -> Dict[str, Any]:
        """Returns nodes and links for UI graph rendering."""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM lineage_records ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()

        nodes = []
        links = []
        seen_nodes = set()

        for r in rows:
            node_id = f"{r['item_type']}:{r['item_id']}"
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                nodes.append({
                    "id": node_id,
                    "type": r["item_type"],
                    "label": r["item_label"],
                    "source_db": r["source_db"],
                    "source_table": r["source_table"],
                    "source_query": r["source_query"],
                })

            if r["parent_id"]:
                parent_node_id = r["parent_id"]
                links.append({
                    "source": parent_node_id,
                    "target": node_id,
                    "relation": "DERIVED_FROM",
                })
            elif r["source_table"]:
                db_table_id = f"TABLE:{r['source_db']}.{r['source_table']}"
                if db_table_id not in seen_nodes:
                    seen_nodes.add(db_table_id)
                    nodes.append({
                        "id": db_table_id,
                        "type": "TABLE",
                        "label": f"{r['source_db']}.{r['source_table']}",
                        "source_db": r["source_db"],
                        "source_table": r["source_table"],
                    })
                links.append({
                    "source": db_table_id,
                    "target": node_id,
                    "relation": "QUERIES",
                })

        return {"nodes": nodes, "links": links}


lineage_tracker = LineageTracker()
