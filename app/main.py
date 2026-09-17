import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.api.routes_databases import router as databases_router
from app.api.routes_discovery import router as discovery_router
from app.api.routes_profiling import router as profiling_router
from app.api.routes_quality import router as quality_router
from app.api.routes_kpi import router as kpi_router
from app.api.routes_analytics import router as analytics_router
from app.api.routes_anomaly import router as anomaly_router
from app.api.routes_rules import router as rules_router
from app.api.routes_insights import router as insights_router
from app.api.routes_reports import router as reports_router
from app.api.routes_query import router as query_router
from app.api.routes_audit import router as audit_router

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Nexuloom Data Intelligence Platform - Production-grade analytics engine",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_cache_headers(request, call_next):
    response = await call_next(request)
    path = request.url.path
    # Allow browser bookmark bar and icons to be cached cleanly
    if any(k in path for k in ["favicon", "apple-touch-icon", ".ico", ".png"]):
        response.headers["Cache-Control"] = "public, max-age=86400"
    return response

# Register API Routers
app.include_router(databases_router)
app.include_router(discovery_router)
app.include_router(profiling_router)
app.include_router(quality_router)
app.include_router(kpi_router)
app.include_router(analytics_router)
app.include_router(anomaly_router)
app.include_router(rules_router)
app.include_router(insights_router)
app.include_router(reports_router)
app.include_router(query_router)
app.include_router(audit_router)


@app.get("/api/health")
def health_check():
    return {
        "status": "HEALTHY",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.UDI_ENV,
    }


# Frontend static files mounting
frontend_dir = settings.BASE_DIR / "frontend"
if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")

    @app.api_route("/", methods=["GET", "HEAD"])
    def serve_dashboard():
        return FileResponse(str(frontend_dir / "index.html"))

    @app.api_route("/favicon.ico", methods=["GET", "HEAD"], include_in_schema=False)
    def serve_favicon():
        fav_ico = frontend_dir / "favicon.ico"
        if not fav_ico.exists():
            fav_ico = frontend_dir / "img" / "favicon.ico"
        return FileResponse(str(fav_ico), media_type="image/x-icon")

    @app.api_route("/favicon-16x16.png", methods=["GET", "HEAD"], include_in_schema=False)
    def serve_favicon_16():
        return FileResponse(str(frontend_dir / "favicon-16x16.png"), media_type="image/png")

    @app.api_route("/favicon-32x32.png", methods=["GET", "HEAD"], include_in_schema=False)
    def serve_favicon_32():
        return FileResponse(str(frontend_dir / "favicon-32x32.png"), media_type="image/png")

    @app.api_route("/favicon-48x48.png", methods=["GET", "HEAD"], include_in_schema=False)
    def serve_favicon_48():
        return FileResponse(str(frontend_dir / "favicon-48x48.png"), media_type="image/png")

    @app.api_route("/apple-touch-icon.png", methods=["GET", "HEAD"], include_in_schema=False)
    @app.api_route("/apple-touch-icon-precomposed.png", methods=["GET", "HEAD"], include_in_schema=False)
    def serve_apple_touch_icon():
        touch = frontend_dir / "apple-touch-icon.png"
        if not touch.exists():
            touch = frontend_dir / "img" / "apple-touch-icon.png"
        return FileResponse(str(touch), media_type="image/png")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
