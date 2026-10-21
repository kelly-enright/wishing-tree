"""Logging in, logging out, and choosing which side you are here for."""

from __future__ import annotations

import time

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from backend import accounts, config, db

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginForm(BaseModel):
    email: str
    password: str = Field(repr=False)


class SideForm(BaseModel):
    role: str


class ResetForm(BaseModel):
    email: str
    code: str
    password: str = Field(repr=False)


def _set_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        accounts.COOKIE_NAME, token,
        httponly=True,                       # JavaScript cannot read it, so an
                                             # injected script cannot steal it
        samesite="lax",                      # not sent from another site's form
        secure=config.COOKIE_SECURE,         # https only, off for local http
        max_age=int(accounts.SESSION_TTL.total_seconds()),
        path="/",
    )


def _me(session: accounts.Session, roles: list[accounts.Role]) -> dict:
    """What the browser is told about the person signed in.

    The email is included because it is their own, and the account menu shows
    it. Nothing else about the account leaves the server — no hash, no
    session token, no other account's anything.
    """
    return {
        "email": session.email,
        "role": session.role,
        "alias": session.alias,
        "zip": next((r.zip for r in roles if r.role == session.role), None),
        "roles": [{"role": r.role, "alias": r.alias, "zip": r.zip} for r in roles],
    }


@router.get("/me")
def me(session_cookie: str | None = Cookie(default=None, alias=accounts.COOKIE_NAME)) -> dict:
    with db.connect() as conn:
        session = accounts.read_session(conn, session_cookie)
        if session is None:
            return {"signed_in": False}
        roles = accounts.roles_for(conn, session.email)
    return {"signed_in": True, **_me(session, roles)}


@router.post("/login")
def login(form: LoginForm, response: Response) -> dict:
    email = accounts.clean_email(form.email)

    # Wait before answering, for as long as this address's recent failures
    # have earned. Done before the check so a correct password cannot be used
    # to measure whether the delay applied.
    delay = accounts.failure_delay(email)
    if delay:
        time.sleep(delay)

    with db.connect() as conn:
        if not accounts.check_login(conn, email, form.password):
            accounts.record_failure(email)
            conn.commit()
            # One message for a wrong address and a wrong password alike,
            # so this endpoint cannot be used to find out who has an account.
            raise HTTPException(
                status_code=401, detail="That email and password don't match.")

        accounts.clear_failures(email)
        roles = accounts.roles_for(conn, email)
        if not roles:
            raise HTTPException(
                status_code=403,
                detail="That account has no neighbor or wish granter profile yet.",
            )
        only = roles[0] if len(roles) == 1 else None
        token = accounts.start_session(
            conn, email,
            role=only.role if only else None,
            alias=only.alias if only else None,
        )
        conn.commit()
        session = accounts.read_session(conn, token)

    _set_cookie(response, token)
    return {"signed_in": True, "must_choose": only is None, **_me(session, roles)}


@router.post("/side")
def choose_side(
    form: SideForm, response: Response,
    session_cookie: str | None = Cookie(default=None, alias=accounts.COOKIE_NAME),
) -> dict:
    """Pick a side, or move to the other one later from the account menu."""
    with db.connect() as conn:
        session = accounts.read_session(conn, session_cookie)
        if session is None:
            raise HTTPException(status_code=401, detail="Please log in to see this.")
        roles = accounts.roles_for(conn, session.email)
        wanted = next((r for r in roles if r.role == form.role), None)
        if wanted is None:
            raise HTTPException(status_code=403, detail="That isn't your account.")
        accounts.choose_side(conn, session_cookie, wanted)
        conn.commit()
        session = accounts.read_session(conn, session_cookie)
    return {"signed_in": True, **_me(session, roles)}


class DemoForm(BaseModel):
    alias: str


@router.post("/demo")
def demo_login(form: DemoForm, response: Response) -> dict:
    """The "Continue as…" shortcut, for the seeded accounts only.

    It exists so the app can be tried without signing up, and it logs in
    properly rather than going around the login. The email is never sent to
    the browser — the demo list is aliases only, and it stays that way — so
    the alias is resolved here instead.

    The guard that matters: this works only while that account still has the
    published demo password. The moment somebody sets a real one, their
    account stops being reachable this way, so the shortcut can never become
    a back door into a real person's wishes.
    """
    alias = form.alias.strip()
    table = "families" if alias.startswith("Neighbor") else "donors"
    role = "family" if alias.startswith("Neighbor") else "donor"

    with db.connect() as conn:
        row = conn.execute(
            f"SELECT contact_email FROM {table} WHERE alias = ?", (alias,)
        ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="That demo account doesn't exist.")
        email = row["contact_email"].lower()

        if not accounts.check_login(conn, email, config.DEMO_PASSWORD):
            raise HTTPException(
                status_code=403,
                detail=("That account has a password of its own now, so the demo "
                        "shortcut can't open it. Please log in."),
            )

        wanted = next((r for r in accounts.roles_for(conn, email) if r.role == role), None)
        if wanted is None:
            raise HTTPException(status_code=404, detail="That demo account doesn't exist.")
        token = accounts.start_session(conn, email, role=wanted.role, alias=wanted.alias)
        conn.commit()
        session = accounts.read_session(conn, token)
        roles = accounts.roles_for(conn, email)

    _set_cookie(response, token)
    return {"signed_in": True, **_me(session, roles)}


@router.post("/logout")
def logout(
    response: Response,
    session_cookie: str | None = Cookie(default=None, alias=accounts.COOKIE_NAME),
) -> dict:
    """Just signs out. There is a password now, so coming back is easy."""
    with db.connect() as conn:
        accounts.end_session(conn, session_cookie)
        conn.commit()
    response.delete_cookie(accounts.COOKIE_NAME, path="/")
    return {"signed_in": False}


@router.post("/reset")
def reset_with_code(form: ResetForm, response: Response) -> dict:
    """Set a new password using a code a coordinator read out."""
    email = accounts.clean_email(form.email)
    with db.connect() as conn:
        if not accounts.spend_reset_code(conn, email, form.code):
            conn.commit()
            raise HTTPException(
                status_code=400,
                detail="That code isn't right, or it has expired. Ask the coordinator for a new one.",
            )
        accounts.set_password(conn, email, form.password)
        # Whoever was signed in on this account, is not now. A reset is also
        # what you do when you think somebody else is in there.
        accounts.end_all_sessions(conn, email)
        conn.commit()
    response.delete_cookie(accounts.COOKIE_NAME, path="/")
    return {"ok": True, "message": "Your password is set. You can log in now."}
