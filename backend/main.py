"""FastAPI app for Wishing Tree.

It serves two things from one process on one port:
  - the JSON API under /api
  - the BUILT React frontend (frontend/dist), committed to the repo

so running this project needs Python only — no Node, no second server.

Startup order: check the key, create the database, seed it if empty. A missing
PORTKEY_API_KEY stops the app with a message naming both paths it looked in.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend import config, db, seed

STARTUP: dict[str, object] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    config.require_api_key()          # stops here with a clear message if absent
    db.init_db()
    STARTUP["counts"] = seed.seed_if_empty()
    yield


app = FastAPI(title="Wishing Tree", version="0.1.0", lifespan=lifespan)


# --------------------------------------------------------------------------
# API
# --------------------------------------------------------------------------

@app.get("/api/health")
def health() -> dict:
    """Enough to prove the whole stack is wired: key, database, region, build."""
    key_ok, key_note = config.api_key_status()
    with db.connect() as conn:
        counts = db.counts(conn)
    region = config.get_region()
    return {
        "status": "ok",
        "model": config.MODEL_NAME,
        "api_key_found": key_ok,
        "api_key_note": key_note if not key_ok else "found",
        "database": str(config.DB_PATH),
        "counts": counts,
        "region": {
            "name": region.name,
            "hub_name": region.hub_name,
            "hub_address": region.hub_address,
            "dropoff_window": region.dropoff_window.label(),
            "delivery_window": region.delivery_window.label(),
        },
        "frontend_built": config.FRONTEND_DIST.joinpath("index.html").exists(),
    }


# --------------------------------------------------------------------------
# Built frontend
# --------------------------------------------------------------------------

_INDEX = config.FRONTEND_DIST / "index.html"

if (config.FRONTEND_DIST / "assets").is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=config.FRONTEND_DIST / "assets"),
        name="assets",
    )


@app.get("/{full_path:path}")
def spa(full_path: str):
    """Serve a built file when it exists, otherwise index.html (SPA routing)."""
    if full_path.startswith("api/"):
        return JSONResponse({"detail": "Not Found"}, status_code=404)

    if full_path:
        candidate = (config.FRONTEND_DIST / full_path).resolve()
        dist = config.FRONTEND_DIST.resolve()
        if candidate.is_file() and candidate.is_relative_to(dist):
            return FileResponse(candidate)

    if not _INDEX.exists():
        return JSONResponse(
            {
                "detail": "The frontend is not built.",
                "fix": "cd frontend && npm install && npm run build",
                "note": "The built frontend is committed, so a fresh clone "
                        "should already have it.",
            },
            status_code=503,
        )
    return FileResponse(_INDEX)
