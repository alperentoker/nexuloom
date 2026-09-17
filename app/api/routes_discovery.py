from fastapi import APIRouter, HTTPException, Query
from app.discovery.schema import SchemaDiscoverer
from app.discovery.relationship import RelationshipDiscoverer

router = APIRouter(prefix="/api/discovery", tags=["Schema Discovery"])


@router.get("/catalog/{db_name}")
def get_catalog(db_name: str, refresh: bool = Query(False)):
    try:
        discoverer = SchemaDiscoverer(db_name)
        catalog = discoverer.discover_catalog(use_cache=not refresh)
        return catalog
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/table/{db_name}/{table_name}")
def get_table_details(db_name: str, table_name: str):
    try:
        discoverer = SchemaDiscoverer(db_name)
        return discoverer.inspect_table(table_name)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/relationships/{db_name}")
def get_relationships(db_name: str):
    try:
        discoverer = SchemaDiscoverer(db_name)
        rel_discoverer = RelationshipDiscoverer(discoverer)
        return rel_discoverer.discover_relationships()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
