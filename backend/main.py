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

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend import config, db, seed
from backend.models import (
    AccountSummary,
    CoordinatorUnlock,
    Donor,
    DonorSignUp,
    Family,
    FamilySignUp,
)

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
# Sign-up — the three ways into the app
# --------------------------------------------------------------------------
# There are no passwords in the MVP. Signing up creates the record and returns
# the alias; the browser remembers that alias so the person can come back.
# Addresses and phone numbers arrive here through a plain form and go straight
# to the database for the coordinator. They are never sent to a model.


def _check_region(zip_code: str) -> None:
    if config.region_for_zip(zip_code) is None:
        active = ", ".join(r.name for r in config.active_regions())
        raise HTTPException(
            status_code=400,
            detail=f"Wishing Tree is not in {zip_code} yet. Right now we cover {active}.",
        )


@app.post("/api/families", status_code=201)
def create_family(form: FamilySignUp) -> dict:
    _check_region(form.zip)
    region = config.region_for_zip(form.zip)
    with db.connect() as conn:
        family = Family(
            alias=db.next_family_alias(conn),
            zip=form.zip,
            region_slug=region.slug,
            contact_address=form.contact_address,
            contact_phone=form.contact_phone,
        )
        db.insert_family(family, conn)
        conn.commit()
    return {"role": "family", **family.public_view()}


@app.post("/api/donors", status_code=201)
def create_donor(form: DonorSignUp) -> dict:
    _check_region(form.zip)
    region = config.region_for_zip(form.zip)
    with db.connect() as conn:
        donor = Donor(
            alias=db.next_donor_alias(conn),
            zip=form.zip,
            region_slug=region.slug,
            contact_address=form.contact_address,
            contact_phone=form.contact_phone,
            budget_usd=form.budget_usd,
            preferred_categories=form.preferred_categories,
            preference=form.preference,
        )
        db.insert_donor(donor, conn)
        conn.commit()
    return {"role": "donor", **donor.public_view()}


@app.get("/api/accounts")
def list_accounts() -> dict[str, list[AccountSummary]]:
    """The demo "Continue as..." list: aliases and zips only.

    Deliberately returns public_view() shapes. No street address and no phone
    number can reach this endpoint, which is what makes an open list of
    accounts safe to show a tester.
    """
    with db.connect() as conn:
        wishes = db.wish_counts_by_family(conn)
        families = [
            AccountSummary(
                role="family",
                alias=f.alias,
                zip=f.zip,
                detail=f"{wishes.get(f.alias, 0)} wishes",
            )
            for f in db.list_families(conn)
        ]
        donors = [
            AccountSummary(
                role="donor",
                alias=d.alias,
                zip=d.zip,
                detail=f"${d.budget_usd:,.0f} budget",
            )
            for d in db.list_donors(conn)
        ]
    return {"families": families, "donors": donors}


@app.get("/api/accounts/{role}/{alias}")
def get_account(role: str, alias: str) -> dict:
    """Confirm a remembered alias still exists when the browser comes back."""
    with db.connect() as conn:
        record = db.get_family(conn, alias) if role == "family" else db.get_donor(conn, alias)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No {role} with alias {alias!r}.")
    return {"role": role, **record.public_view()}


@app.post("/api/coordinator/unlock")
def coordinator_unlock(body: CoordinatorUnlock) -> dict:
    """The coordinator screens show addresses and phone numbers, so they are
    behind a shared passcode. Checked here on the server, never in the browser."""
    if body.passcode.strip() != config.COORDINATOR_PASSCODE:
        raise HTTPException(status_code=401, detail="That passcode is not right.")
    return {"role": "coordinator", "unlocked": True}


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
