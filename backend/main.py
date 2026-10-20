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

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend import config, db, safety_checks, seed
from backend.agents import budget as budget_module
from backend.coordinator_api import router as coordinator_router
from backend.coordinator_auth import issue_token, require_coordinator
from backend.donor_api import router as donor_router
from backend.family_api import router as family_router
from backend.intake_api import router as intake_router
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
app.include_router(intake_router)
app.include_router(donor_router)
app.include_router(family_router)
app.include_router(coordinator_router)


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
            detail=config.OUT_OF_AREA_MESSAGE.format(zip=zip_code, region=active),
        )


def _check_email(email: str) -> str:
    """A typo in an email should read as a typo, not as a server error."""
    cleaned = (email or "").strip()
    local, _, domain = cleaned.partition("@")
    if not local or "." not in domain or domain.endswith("."):
        raise HTTPException(
            status_code=400,
            detail="That email address doesn't look right — have another look "
                   "and try again.",
        )
    return cleaned


@app.get("/api/retailers")
def retailers() -> dict:
    """The stores a product link may point at.

    The interface shows a few of these next to the link field, so a family
    knows before pasting rather than after. Checking a link is string work:
    nothing in this app ever opens one.
    """
    stores = sorted(config.RETAILER_ALLOWLIST)
    return {
        "count": len(stores),
        "stores": stores,
        "note": "Links from anywhere else can't be posted, but you can still "
                "describe what you need and a neighbor will choose it.",
    }


@app.get("/api/service-area")
def service_area(zip: str | None = None) -> dict:
    """Is this zip in the area? Asked as soon as the field is filled in, so
    nobody gets to the end of a form only to be turned away."""
    region = config.get_region()
    base = {
        "notice": config.SERVICE_AREA_NOTICE,
        "region": region.name,
        "zip_codes": region.zip_codes,
    }
    if not zip:
        return {**base, "checked": False}

    covered = config.region_for_zip(zip) is not None
    return {
        **base,
        "checked": True,
        "zip": zip,
        "covered": covered,
        "message": (
            f"You're in the area — we deliver across {region.name}."
            if covered
            else config.OUT_OF_AREA_MESSAGE.format(zip=zip, region=region.name)
        ),
    }


@app.post("/api/families", status_code=201)
def create_family(form: FamilySignUp) -> dict:
    _check_region(form.zip)
    email = _check_email(form.contact_email)
    region = config.region_for_zip(form.zip)
    with db.connect() as conn:
        family = Family(
            alias=db.next_family_alias(conn),
            zip=form.zip,
            region_slug=region.slug,
            contact_address=form.contact_address,
            contact_email=email,
            contact_phone=form.contact_phone or None,
        )
        db.insert_family(family, conn)
        conn.commit()
    return {"role": "family", **family.public_view()}


@app.post("/api/donors", status_code=201)
def create_donor(form: DonorSignUp) -> dict:
    _check_region(form.zip)
    email = _check_email(form.contact_email)
    region = config.region_for_zip(form.zip)
    with db.connect() as conn:
        donor = Donor(
            alias=db.next_donor_alias(conn),
            zip=form.zip,
            region_slug=region.slug,
            contact_address=form.contact_address,
            contact_email=email,
            contact_phone=form.contact_phone or None,
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
    behind a shared passcode, checked here on the server.

    A correct passcode issues a token (see `coordinator_auth`). Coordinator
    data is served against that token, so those endpoints are closed rather
    than merely hidden.
    """
    return {
        "role": "coordinator",
        "unlocked": True,
        "token": issue_token(body.passcode),
    }


@app.get("/api/coordinator/activity", dependencies=[Depends(require_coordinator)])
def coordinator_activity(limit: int = 200) -> dict:
    """Every agent call, newest last, with what it did and what it cost.

    Two things keep family details off this page, in this order:

      1. Nothing written into a call summary is family text. The server
         composes both summaries from structured values it already holds —
         intake records *how long* a message was, never what it said, and
         safety records verdicts and the kinds of things removed. There is no
         code path that copies a family's words into these fields.
      2. `scrub()` runs over both on the way out, which removes phone numbers,
         emails and street addresses by pattern.

    The first is the guarantee; the second is a net under it. A bare name with
    no lead-in phrase would not be caught by pattern alone, which is exactly
    why the summaries are built from structure rather than from text.
    """
    with db.connect() as conn:
        calls = db.list_agent_calls(conn)
        reviews = {r["request_id"]: r for r in db.list_safety_reviews(conn) if r}
        daily = budget_module.tokens_today(conn)

    rows = []
    for call in calls[-limit:]:
        review = reviews.get(call["request_id"]) if call["request_id"] else None
        rows.append({
            "timestamp": call["timestamp"],
            "agent": call["agent"],
            "operation": call["operation"],
            "session_id": call["session_id"],
            "request_id": call["request_id"],
            "tools_called": [t for t in (call["tools_called"] or "").split(",") if t],
            "input_summary": safety_checks.scrub(call["input_summary"]),
            "output_summary": safety_checks.scrub(call["output_summary"]),
            "removed": review["removed"] if review else [],
            "flags": review["flags"] if review else [],
            "enforced": review["enforced"] if review else [],
            "input_tokens": call["input_tokens"],
            "cached_input_tokens": call["cached_input_tokens"],
            "cache_write_tokens": call["cache_write_tokens"],
            "output_tokens": call["output_tokens"],
            "latency_ms": call["latency_ms"],
            "cost_usd": call["estimated_cost_usd"],
            "ok": bool(call["ok"]),
            "error": call["error"],
            "prompt_version": call["prompt_version"],
        })

    totals = {
        "calls": len(calls),
        "input_tokens": sum(c["input_tokens"] for c in calls),
        "cached_input_tokens": sum(c["cached_input_tokens"] for c in calls),
        "cache_write_tokens": sum(c["cache_write_tokens"] for c in calls),
        "output_tokens": sum(c["output_tokens"] for c in calls),
        "cost_usd": sum(c["estimated_cost_usd"] or 0 for c in calls),
        "prices_are_placeholders": config.PRICES_ARE_PLACEHOLDERS,
    }
    return {
        "calls": rows,
        "totals": totals,
        "budget": {
            "daily_tokens": daily,
            "daily_cap": config.DAILY_TOKEN_BUDGET,
            "daily_remaining": max(0, config.DAILY_TOKEN_BUDGET - daily),
            "session_cap": config.MAX_TOKENS_PER_INTAKE_SESSION,
        },
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
