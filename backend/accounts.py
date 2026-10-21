"""Accounts: passwords, sessions, and who a request is allowed to be.

Three rules shape everything here.

**A password is never stored.** Only a bcrypt hash, which is deliberately slow
to compute and salted per account, so two people with the same password have
nothing in common on disk. Nothing in this module returns, logs or formats a
password, and there is no column in the schema that could hold one.

**A token is never stored either.** A session cookie and a reset code are both
credentials; what goes in the database is a SHA-256 of each. Someone who reads
the tables cannot log in with what they find, and a stolen cookie still has to
be the cookie.

**One email may hold two accounts.** A neighbor who asks in March and gives in
December is the point of a tree that stays up all year, so an account is keyed
on email and the roles are whatever that email matches. The session remembers
which side the person is currently on.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Cookie, HTTPException

from backend import config, db

COOKIE_NAME = "wishingtree_session"
SESSION_TTL = timedelta(days=14)
RESET_TTL = timedelta(hours=1)

MIN_PASSWORD = 8

# Failed logins, per email, in memory. Not per IP: behind one coffee-shop
# router everybody shares an address, and locking a neighbor out because a
# stranger guessed badly is a worse failure than the one being prevented.
_FAILURES: dict[str, list[float]] = {}
FAILURE_WINDOW = 15 * 60          # seconds we remember a failure for
FREE_ATTEMPTS = 5                 # before any delay at all
MAX_DELAY = 8.0                   # seconds


# --------------------------------------------------------------------------
# Hashing
# --------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """A bcrypt hash, salt included, ready to store."""
    check_password_strength(password)
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(config.BCRYPT_ROUNDS)).decode()


def verify_password(password: str, stored: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), stored.encode())
    except (ValueError, TypeError):
        return False        # a malformed hash is a failed login, not a crash


def check_password_strength(password: str) -> None:
    """Length, and nothing else.

    No "one capital, one symbol" rule. Those push people towards Passw0rd!
    and away from the long ordinary phrases that are actually hard to guess,
    which is why NIST stopped recommending them.
    """
    if len(password) < MIN_PASSWORD:
        raise HTTPException(
            status_code=400,
            detail=f"Please choose a password of at least {MIN_PASSWORD} characters.",
        )


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# --------------------------------------------------------------------------
# Email
# --------------------------------------------------------------------------

_EMAIL = re.compile(r"^[^@\s]+@[^@\s.]+\.[^@\s]+$")


def clean_email(email: str) -> str:
    email = (email or "").strip().lower()
    if not _EMAIL.match(email):
        raise HTTPException(status_code=400, detail="That email address doesn't look right.")
    return email


# --------------------------------------------------------------------------
# Slowing down guesses
# --------------------------------------------------------------------------

def _recent_failures(email: str) -> int:
    now = time.monotonic()
    kept = [t for t in _FAILURES.get(email, []) if now - t < FAILURE_WINDOW]
    if kept:
        _FAILURES[email] = kept
    else:
        _FAILURES.pop(email, None)
    return len(kept)


def failure_delay(email: str) -> float:
    """How long this attempt should be made to wait.

    Five free attempts, because real people mistype. After that the delay
    doubles each time to a ceiling: the sixth attempt waits half a second,
    the tenth waits eight, and a script trying a dictionary gets perhaps a
    dozen guesses a minute instead of thousands.
    """
    over = _recent_failures(email) - FREE_ATTEMPTS
    if over < 0:
        return 0.0
    return min(MAX_DELAY, 0.5 * (2 ** over))


def record_failure(email: str) -> None:
    _FAILURES.setdefault(email, []).append(time.monotonic())


def clear_failures(email: str) -> None:
    _FAILURES.pop(email, None)


def reset_throttle() -> None:
    """For tests, which must not inherit another test's failures."""
    _FAILURES.clear()


# --------------------------------------------------------------------------
# Accounts
# --------------------------------------------------------------------------

def create_account(conn: sqlite3.Connection, email: str, password: str) -> None:
    """Store an email and the hash of its password. Never the password."""
    conn.execute(
        "INSERT INTO accounts (email, password_hash, created_at) VALUES (?, ?, ?)",
        (email, hash_password(password), _now_text()),
    )


def account_exists(conn: sqlite3.Connection, email: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM accounts WHERE email = ?", (email,)
    ).fetchone() is not None


def set_password(conn: sqlite3.Connection, email: str, password: str) -> None:
    conn.execute(
        "UPDATE accounts SET password_hash = ? WHERE email = ?",
        (hash_password(password), email),
    )


def check_login(conn: sqlite3.Connection, email: str, password: str) -> bool:
    row = conn.execute(
        "SELECT password_hash FROM accounts WHERE email = ?", (email,)
    ).fetchone()
    if row is None:
        # Spend the time anyway. Answering instantly for an unknown address
        # and slowly for a known one tells an attacker which is which.
        bcrypt.checkpw(b"x", bcrypt.hashpw(b"x", bcrypt.gensalt(config.BCRYPT_ROUNDS)))
        return False
    return verify_password(password, row["password_hash"])


@dataclass(frozen=True)
class Role:
    role: str          # "family" | "donor"
    alias: str
    zip: str


def roles_for(conn: sqlite3.Connection, email: str) -> list[Role]:
    """Every side of the app this email can act as, neighbor first."""
    out: list[Role] = []
    for row in conn.execute(
        "SELECT alias, zip FROM families WHERE lower(contact_email) = ? ORDER BY id", (email,)
    ):
        out.append(Role("family", row["alias"], row["zip"]))
    for row in conn.execute(
        "SELECT alias, zip FROM donors WHERE lower(contact_email) = ? ORDER BY id", (email,)
    ):
        out.append(Role("donor", row["alias"], row["zip"]))
    return out


# --------------------------------------------------------------------------
# Sessions
# --------------------------------------------------------------------------

def own_family_aliases(conn: sqlite3.Connection, email: str | None) -> list[str]:
    """The neighbor aliases this email holds, if any.

    Used to keep a person's own wishes off their own tree. Empty for a granter
    who has no neighbor account, which is almost everybody.
    """
    if not email:
        return []
    return [
        row["alias"] for row in conn.execute(
            "SELECT alias FROM families WHERE lower(contact_email) = ?", (email,))
    ]


@dataclass(frozen=True)
class Session:
    email: str
    role: str | None
    alias: str | None


def start_session(conn: sqlite3.Connection, email: str,
                  role: str | None = None, alias: str | None = None) -> str:
    """Open a session and return the token that belongs in the cookie."""
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    conn.execute(
        """INSERT INTO sessions (token_hash, email, role, alias, created_at, expires_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (_token_hash(token), email, role, alias,
         now.isoformat(), (now + SESSION_TTL).isoformat()),
    )
    return token


def read_session(conn: sqlite3.Connection, token: str | None) -> Session | None:
    if not token:
        return None
    row = conn.execute(
        "SELECT email, role, alias, expires_at FROM sessions WHERE token_hash = ?",
        (_token_hash(token),),
    ).fetchone()
    if row is None:
        return None
    if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
        end_session(conn, token)
        return None
    return Session(row["email"], row["role"], row["alias"])


def choose_side(conn: sqlite3.Connection, token: str, role: Role) -> None:
    conn.execute(
        "UPDATE sessions SET role = ?, alias = ? WHERE token_hash = ?",
        (role.role, role.alias, _token_hash(token)),
    )


def end_session(conn: sqlite3.Connection, token: str | None) -> None:
    if token:
        conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))


def end_all_sessions(conn: sqlite3.Connection, email: str) -> None:
    """Used after a password reset: whoever was signed in, is not now."""
    conn.execute("DELETE FROM sessions WHERE email = ?", (email,))


# --------------------------------------------------------------------------
# Reset codes
# --------------------------------------------------------------------------

_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # no I/O/0/1 to read out


def issue_reset_code(conn: sqlite3.Connection, email: str) -> str:
    """A short code a coordinator can read down a phone. Returned once."""
    raw = "".join(secrets.choice(_CODE_ALPHABET) for _ in range(8))
    code = f"{raw[:4]}-{raw[4:]}"
    now = datetime.now(timezone.utc)
    conn.execute("DELETE FROM password_resets WHERE email = ? AND used_at IS NULL", (email,))
    conn.execute(
        """INSERT INTO password_resets (code_hash, email, created_at, expires_at)
           VALUES (?, ?, ?, ?)""",
        (_token_hash(code), email, now.isoformat(), (now + RESET_TTL).isoformat()),
    )
    return code


def spend_reset_code(conn: sqlite3.Connection, email: str, code: str) -> bool:
    """Check a code and burn it. True only if it was valid, unused and live."""
    now = datetime.now(timezone.utc)
    row = conn.execute(
        """SELECT code_hash, expires_at, used_at FROM password_resets
            WHERE code_hash = ? AND email = ?""",
        (_token_hash(code.strip().upper()), email),
    ).fetchone()
    if row is None or row["used_at"] is not None:
        return False
    if datetime.fromisoformat(row["expires_at"]) < now:
        return False
    conn.execute(
        "UPDATE password_resets SET used_at = ? WHERE code_hash = ?",
        (now.isoformat(), row["code_hash"]),
    )
    return True


def _now_text() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------
# What a request is allowed to be
# --------------------------------------------------------------------------

def current(session_cookie: str | None = Cookie(default=None, alias=COOKIE_NAME)
            ) -> Session | None:
    """The session behind this request, or None. Never raises."""
    with db.connect() as conn:
        return read_session(conn, session_cookie)


def require(role: str | None = None):
    """A dependency that insists on a signed-in session, optionally a role.

    This is the thing that makes an alias in a URL harmless. Before accounts,
    `/api/families/Neighbor A04/wishes` trusted whoever typed it; now the
    alias has to match the session, so the URL is a route rather than a key.
    """
    def dependency(
        session_cookie: str | None = Cookie(default=None, alias=COOKIE_NAME),
    ) -> Session:
        with db.connect() as conn:
            session = read_session(conn, session_cookie)
        if session is None:
            raise HTTPException(status_code=401, detail="Please log in to see this.")
        if session.role is None:
            raise HTTPException(status_code=409, detail="Choose which side you're here for.")
        if role is not None and session.role != role:
            raise HTTPException(status_code=403, detail="That isn't your account.")
        return session
    return dependency


def owns(session: Session, alias: str) -> None:
    """Refuse a request for somebody else's alias."""
    if session.alias != alias:
        raise HTTPException(status_code=403, detail="That isn't your account.")
