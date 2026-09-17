#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Ensure root directory is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn
from app.core.config import settings
from app.database.registry import connection_registry
from scripts.seed_demo_db import generate_synthetic_enterprise_db


def initialize_platform():
    """Initializes platform storage, verifies demo database, and checks readiness."""
    settings.ensure_directories()

    # Check if demo_enterprise exists, if not, auto-seed it
    demo_db_file = settings.UDI_DATA_DIR / "demo_enterprise.db"
    conns = connection_registry.list_connections()

    if not demo_db_file.exists() or len(conns) == 0:
        print("🌱 Initializing platform: Auto-seeding enterprise demo database...")
        generate_synthetic_enterprise_db()
        print("✓ Enterprise demo database initialized successfully.")

    # Auto-discover any active SQLite databases in workspace
    discovered = connection_registry.auto_discover_local_sqlite()
    if discovered:
        print(f"🔍 Discovered and registered {len(discovered)} active local project database(s): {[d['name'] for d in discovered]}")


import socket


def find_available_port(preferred_port: int = 8000, max_attempts: int = 50) -> int:
    """Checks if preferred_port is available; if not, finds the next free port."""
    for p in range(preferred_port, preferred_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("0.0.0.0", p))
                return p
            except OSError:
                continue
    return preferred_port


def main():
    initialize_platform()

    host = os.getenv("HOST", "0.0.0.0")
    requested_port = int(os.getenv("PORT", "8001"))
    port = find_available_port(requested_port)

    if port != requested_port:
        print(f"⚠️ Port {requested_port} is currently in use. Automatically switched to available port {port}.")

    print("\n" + "=" * 70)
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION}")
    print("=" * 70)
    print(f"• Web Dashboard:     http://localhost:{port}")
    print(f"• API Documentation: http://localhost:{port}/docs")
    print(f"• Environment:       {settings.UDI_ENV}")
    print(f"• Data Directory:    {settings.UDI_DATA_DIR}")
    print(f"• Reports Directory: {settings.UDI_REPORTS_DIR}")
    print("=" * 70 + "\n")

    uvicorn.run("app.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    main()
