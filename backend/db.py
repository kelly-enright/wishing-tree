"""SQLite storage for Wishing Tree.

One file at data/wishing_tree.db, created automatically on first run. Plain
sqlite3 on purpose: no migrations to run, nothing to install, and the teaching
staff need only Python. The Pydantic models in backend/models.py are the typed
layer on top; every function here takes or returns one of them.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from backend import config
from backend.models import (
    AgentCallLog,
    Donor,
    Family,
    IntakeSession,
    Pledge,
    PledgeStatus,
    Request,
    RequestStatus,
    WindowResponse,
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS families (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    alias           TEXT    NOT NULL UNIQUE,
    zip             TEXT    NOT NULL,
    region_slug     TEXT    NOT NULL,
    contact_address TEXT    NOT NULL,   -- coordinator only
    contact_email   TEXT    NOT NULL,   -- coordinator only
    contact_phone   TEXT,               -- coordinator only, optional
    created_at      TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS donors (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    alias                TEXT    NOT NULL UNIQUE,
    zip                  TEXT    NOT NULL,
    region_slug          TEXT    NOT NULL,
    contact_address      TEXT    NOT NULL,   -- coordinator only
    contact_email        TEXT    NOT NULL,   -- coordinator only
    contact_phone        TEXT,               -- coordinator only, optional
    budget_usd           REAL    NOT NULL,
    preferred_categories TEXT    NOT NULL,   -- comma separated
    preference           TEXT    NOT NULL,
    created_at           TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS requests (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    family_alias       TEXT    NOT NULL REFERENCES families(alias),
    category           TEXT    NOT NULL,
    request_type       TEXT    NOT NULL,
    item_description   TEXT    NOT NULL,
    deadline           TEXT,
    occasion           TEXT    NOT NULL,
    zip                TEXT    NOT NULL,
    status             TEXT    NOT NULL,
    estimated_cost_usd REAL,
    budget_min_usd     REAL,
    budget_max_usd     REAL,
    product_link       TEXT,
    brand              TEXT,
    size               TEXT,
    color              TEXT,
    open_to_substitute INTEGER NOT NULL DEFAULT 0,
    cost_is_estimate   INTEGER NOT NULL DEFAULT 0,
    size_preferences   TEXT,
    created_at         TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS pledges (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id                INTEGER NOT NULL REFERENCES requests(id),
    donor_alias               TEXT    NOT NULL REFERENCES donors(alias),
    dropoff_date              TEXT    NOT NULL,
    delivery_date             TEXT    NOT NULL,
    window_response           TEXT    NOT NULL DEFAULT 'pending',
    status                    TEXT    NOT NULL,
    created_at                TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS intake_sessions (
    session_id       TEXT    PRIMARY KEY,
    family_alias     TEXT    NOT NULL REFERENCES families(alias),
    started_at       TEXT    NOT NULL,
    approved_at      TEXT,
    turns            INTEGER NOT NULL DEFAULT 0,
    status           TEXT    NOT NULL,
    duration_seconds REAL
);

CREATE TABLE IF NOT EXISTS agent_calls (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp           TEXT    NOT NULL,
    session_id          TEXT,
    agent               TEXT    NOT NULL,
    model               TEXT    NOT NULL,
    operation           TEXT    NOT NULL,
    tools_called        TEXT    NOT NULL DEFAULT '',
    input_summary       TEXT    NOT NULL DEFAULT '',
    output_summary      TEXT    NOT NULL DEFAULT '',
    input_tokens        INTEGER NOT NULL DEFAULT 0,
    cached_input_tokens INTEGER NOT NULL DEFAULT 0,
    cache_write_tokens  INTEGER NOT NULL DEFAULT 0,
    output_tokens       INTEGER NOT NULL DEFAULT 0,
    latency_ms          INTEGER NOT NULL DEFAULT 0,
    estimated_cost_usd  REAL,
    ok                  INTEGER NOT NULL DEFAULT 1,
    error               TEXT,
    request_id          INTEGER,
    prompt_version      TEXT
);

CREATE TABLE IF NOT EXISTS safety_reviews (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    request_id     INTEGER NOT NULL REFERENCES requests(id),
    reviewed_at    TEXT    NOT NULL,
    approved       INTEGER NOT NULL,
    removed        TEXT    NOT NULL DEFAULT '[]',   -- JSON list of kinds, never values
    flags          TEXT    NOT NULL DEFAULT '[]',   -- JSON list of {kind, reason}
    enforced       TEXT    NOT NULL DEFAULT '[]',   -- what the code pass changed
    note_to_family TEXT    NOT NULL DEFAULT '',
    session_id     TEXT
);

CREATE INDEX IF NOT EXISTS idx_reviews_request   ON safety_reviews(request_id);
CREATE INDEX IF NOT EXISTS idx_calls_session     ON agent_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_requests_status   ON requests(status);
CREATE INDEX IF NOT EXISTS idx_requests_zip      ON requests(zip);
CREATE INDEX IF NOT EXISTS idx_requests_deadline ON requests(deadline);
CREATE INDEX IF NOT EXISTS idx_pledges_request   ON pledges(request_id);
"""


# --------------------------------------------------------------------------
# Connection
# --------------------------------------------------------------------------

def connect(db_path: Path | None = None) -> sqlite3.Connection:
    """Open the database, creating the folder and file if needed."""
    path = Path(db_path or config.DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | None = None) -> Path:
    """Create the schema if it is not there. Safe to call on every start."""
    path = Path(db_path or config.DB_PATH)
    with connect(path) as conn:
        conn.executescript(SCHEMA)
    return path


def is_empty(db_path: Path | None = None) -> bool:
    with connect(db_path) as conn:
        row = conn.execute("SELECT COUNT(*) AS n FROM requests").fetchone()
    return row["n"] == 0


# --------------------------------------------------------------------------
# Row <-> model
# --------------------------------------------------------------------------

def _family(row: sqlite3.Row) -> Family:
    return Family(**dict(row))


def _donor(row: sqlite3.Row) -> Donor:
    data = dict(row)
    cats = data.pop("preferred_categories", "") or ""
    return Donor(preferred_categories=[c for c in cats.split(",") if c], **data)


def _request(row: sqlite3.Row) -> Request:
    data = dict(row)
    data["open_to_substitute"] = bool(data["open_to_substitute"])
    data["cost_is_estimate"] = bool(data.get("cost_is_estimate", 0))
    return Request(**data)


def _pledge(row: sqlite3.Row) -> Pledge:
    data = dict(row)
    return Pledge(**data)


def _iso(value: datetime | date) -> str:
    return value.isoformat()


# --------------------------------------------------------------------------
# Writes
# --------------------------------------------------------------------------

def insert_family(family: Family, conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        """INSERT INTO families (alias, zip, region_slug, contact_address,
                                 contact_email, contact_phone, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (family.alias, family.zip, family.region_slug, family.contact_address,
         family.contact_email, family.contact_phone, _iso(family.created_at)),
    )
    return int(cur.lastrowid)


def insert_donor(donor: Donor, conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        """INSERT INTO donors (alias, zip, region_slug, contact_address,
                               contact_email, contact_phone,
                               budget_usd, preferred_categories, preference, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (donor.alias, donor.zip, donor.region_slug, donor.contact_address,
         donor.contact_email, donor.contact_phone, donor.budget_usd,
         ",".join(c.value for c in donor.preferred_categories),
         donor.preference.value, _iso(donor.created_at)),
    )
    return int(cur.lastrowid)


def insert_request(request: Request, conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        """INSERT INTO requests (family_alias, category, request_type, item_description,
                                 deadline, occasion, zip, status, estimated_cost_usd,
                                 budget_min_usd, budget_max_usd, product_link, brand,
                                 size, color, open_to_substitute, cost_is_estimate,
                                 size_preferences, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (request.family_alias, request.category.value, request.request_type.value,
         request.item_description,
         _iso(request.deadline) if request.deadline else None,
         request.occasion.value,
         request.zip, request.status.value, request.estimated_cost_usd,
         request.budget_min_usd, request.budget_max_usd, request.product_link,
         request.brand, request.size, request.color, int(request.open_to_substitute),
         int(request.cost_is_estimate),
         request.size_preferences, _iso(request.created_at)),
    )
    return int(cur.lastrowid)


def insert_pledge(pledge: Pledge, conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        """INSERT INTO pledges (request_id, donor_alias, dropoff_date, delivery_date,
                                window_response, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (pledge.request_id, pledge.donor_alias, _iso(pledge.dropoff_date),
         _iso(pledge.delivery_date), pledge.window_response.value,
         pledge.status.value, _iso(pledge.created_at)),
    )
    return int(cur.lastrowid)


# --------------------------------------------------------------------------
# Reads
# --------------------------------------------------------------------------

def list_families(conn: sqlite3.Connection) -> list[Family]:
    return [_family(r) for r in conn.execute("SELECT * FROM families ORDER BY alias")]


def list_donors(conn: sqlite3.Connection) -> list[Donor]:
    return [_donor(r) for r in conn.execute("SELECT * FROM donors ORDER BY alias")]


def list_requests(
    conn: sqlite3.Connection, status: RequestStatus | None = None
) -> list[Request]:
    if status is None:
        rows = conn.execute("SELECT * FROM requests ORDER BY deadline IS NULL, deadline")
    else:
        rows = conn.execute(
            "SELECT * FROM requests WHERE status = ? ORDER BY deadline IS NULL, deadline",
            (status.value,)
        )
    return [_request(r) for r in rows]


def list_pledges(
    conn: sqlite3.Connection, status: PledgeStatus | None = None
) -> list[Pledge]:
    if status is None:
        rows = conn.execute("SELECT * FROM pledges ORDER BY dropoff_date")
    else:
        rows = conn.execute(
            "SELECT * FROM pledges WHERE status = ? ORDER BY dropoff_date",
            (status.value,),
        )
    return [_pledge(r) for r in rows]


def counts(conn: sqlite3.Connection) -> dict[str, int]:
    out = {}
    for table in ("families", "donors", "requests", "pledges"):
        out[table] = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
    return out


# --------------------------------------------------------------------------
# Aliases and lookups (sign-up)
# --------------------------------------------------------------------------

# The word a user sees. "Neighbor" for both sides of a wish, because that is
# what they are to each other; the letter keeps the two sets apart. The tables
# are still `families` and `donors` in code — renaming columns buys nothing and
# risks a migration, and nobody outside this file reads them.
ALIAS_LABELS = {"families": "Neighbor", "donors": "Granter"}


def _next_alias(conn: sqlite3.Connection, table: str, prefix: str) -> str:
    """Next free alias, e.g. 'Neighbor A59'. Aliases are the only public names."""
    rows = conn.execute(f"SELECT alias FROM {table}").fetchall()
    highest = 0
    for row in rows:
        tail = row["alias"].rsplit(" ", 1)[-1]
        if tail.startswith(prefix) and tail[len(prefix):].isdigit():
            highest = max(highest, int(tail[len(prefix):]))
    label = ALIAS_LABELS[table]
    return f"{label} {prefix}{highest + 1:02d}"


def next_family_alias(conn: sqlite3.Connection) -> str:
    return _next_alias(conn, "families", "A")


def next_donor_alias(conn: sqlite3.Connection) -> str:
    return _next_alias(conn, "donors", "D")


def get_family(conn: sqlite3.Connection, alias: str) -> Family | None:
    row = conn.execute("SELECT * FROM families WHERE alias = ?", (alias,)).fetchone()
    return _family(row) if row else None


def get_donor(conn: sqlite3.Connection, alias: str) -> Donor | None:
    row = conn.execute("SELECT * FROM donors WHERE alias = ?", (alias,)).fetchone()
    return _donor(row) if row else None


def wish_counts_by_family(conn: sqlite3.Connection) -> dict[str, int]:
    rows = conn.execute(
        "SELECT family_alias, COUNT(*) AS n FROM requests GROUP BY family_alias"
    ).fetchall()
    return {r["family_alias"]: r["n"] for r in rows}


# --------------------------------------------------------------------------
# Intake sessions and agent-call logging
# --------------------------------------------------------------------------
# Wishes that count against a family's cap: submitted but not yet claimed by a
# donor. A draft is not submitted, and a granted wish already has a donor.

OPEN_STATUSES = (RequestStatus.PENDING_REVIEW.value, RequestStatus.OPEN.value)


def open_wish_count(conn: sqlite3.Connection, family_alias: str) -> int:
    placeholders = ",".join("?" for _ in OPEN_STATUSES)
    row = conn.execute(
        f"SELECT COUNT(*) AS n FROM requests "
        f"WHERE family_alias = ? AND status IN ({placeholders})",
        (family_alias, *OPEN_STATUSES),
    ).fetchone()
    return row["n"]


def insert_intake_session(session: IntakeSession, conn: sqlite3.Connection) -> None:
    conn.execute(
        """INSERT INTO intake_sessions (session_id, family_alias, started_at,
                                        approved_at, turns, status, duration_seconds)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (session.session_id, session.family_alias, _iso(session.started_at),
         _iso(session.approved_at) if session.approved_at else None,
         session.turns, session.status.value, session.duration_seconds),
    )


def update_intake_session(session: IntakeSession, conn: sqlite3.Connection) -> None:
    conn.execute(
        """UPDATE intake_sessions
              SET approved_at = ?, turns = ?, status = ?, duration_seconds = ?
            WHERE session_id = ?""",
        (_iso(session.approved_at) if session.approved_at else None,
         session.turns, session.status.value, session.duration_seconds,
         session.session_id),
    )


def get_intake_session(conn: sqlite3.Connection, session_id: str) -> IntakeSession | None:
    row = conn.execute(
        "SELECT * FROM intake_sessions WHERE session_id = ?", (session_id,)
    ).fetchone()
    return IntakeSession(**dict(row)) if row else None


def insert_agent_call(call: AgentCallLog, conn: sqlite3.Connection) -> int:
    cur = conn.execute(
        """INSERT INTO agent_calls (timestamp, session_id, agent, model, operation,
                                    tools_called, input_summary, output_summary,
                                    input_tokens, cached_input_tokens,
                                    cache_write_tokens, output_tokens, latency_ms,
                                    estimated_cost_usd,
                                    ok, error, request_id, prompt_version)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (_iso(call.timestamp), call.session_id, call.agent, call.model, call.operation,
         ",".join(call.tools_called), call.input_summary, call.output_summary,
         call.input_tokens, call.cached_input_tokens, call.cache_write_tokens,
         call.output_tokens, call.latency_ms, call.estimated_cost_usd,
         int(call.ok), call.error, call.request_id, call.prompt_version),
    )
    return int(cur.lastrowid)


def session_usage(conn: sqlite3.Connection, session_id: str) -> dict:
    """Totals for the token panel: this session's tokens, cost and calls."""
    row = conn.execute(
        """SELECT COUNT(*)                      AS calls,
                  COALESCE(SUM(input_tokens), 0)        AS input_tokens,
                  COALESCE(SUM(cached_input_tokens), 0) AS cached_input_tokens,
                  COALESCE(SUM(cache_write_tokens), 0)  AS cache_write_tokens,
                  COALESCE(SUM(output_tokens), 0)       AS output_tokens,
                  COALESCE(SUM(estimated_cost_usd), 0)  AS cost_usd,
                  COALESCE(SUM(latency_ms), 0)          AS latency_ms
             FROM agent_calls WHERE session_id = ?""",
        (session_id,),
    ).fetchone()
    return dict(row)


def list_agent_calls(
    conn: sqlite3.Connection, session_id: str | None = None
) -> list[dict]:
    if session_id is None:
        rows = conn.execute("SELECT * FROM agent_calls ORDER BY id")
    else:
        rows = conn.execute(
            "SELECT * FROM agent_calls WHERE session_id = ? ORDER BY id", (session_id,)
        )
    return [dict(r) for r in rows]


# --------------------------------------------------------------------------
# Safety reviews
# --------------------------------------------------------------------------

def insert_safety_review(
    conn: sqlite3.Connection,
    request_id: int,
    approved: bool,
    removed: list[str],
    flags: list[dict],
    enforced: list[str],
    note_to_family: str,
    session_id: str | None = None,
) -> int:
    cur = conn.execute(
        """INSERT INTO safety_reviews (request_id, reviewed_at, approved, removed,
                                       flags, enforced, note_to_family, session_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (request_id, _iso(datetime.now(timezone.utc)), int(approved),
         json.dumps(removed), json.dumps(flags), json.dumps(enforced),
         note_to_family, session_id),
    )
    return int(cur.lastrowid)


def get_safety_review(conn: sqlite3.Connection, request_id: int) -> dict | None:
    row = conn.execute(
        "SELECT * FROM safety_reviews WHERE request_id = ? ORDER BY id DESC LIMIT 1",
        (request_id,),
    ).fetchone()
    if row is None:
        return None
    out = dict(row)
    out["approved"] = bool(out["approved"])
    for field in ("removed", "flags", "enforced"):
        out[field] = json.loads(out[field])
    return out


def list_safety_reviews(conn: sqlite3.Connection) -> list[dict]:
    return [
        get_safety_review(conn, row["request_id"])
        for row in conn.execute(
            "SELECT DISTINCT request_id FROM safety_reviews ORDER BY request_id"
        )
    ]


def update_request_status(
    conn: sqlite3.Connection, request_id: int, status: RequestStatus
) -> None:
    conn.execute(
        "UPDATE requests SET status = ? WHERE id = ?", (status.value, request_id)
    )


def update_request_content(conn: sqlite3.Connection, request: Request) -> None:
    """Write back a wish the safety review rewrote."""
    conn.execute(
        """UPDATE requests
              SET item_description = ?, product_link = ?, brand = ?, size = ?,
                  color = ?, size_preferences = ?, request_type = ?, status = ?
            WHERE id = ?""",
        (request.item_description, request.product_link, request.brand, request.size,
         request.color, request.size_preferences, request.request_type.value,
         request.status.value, request.id),
    )


# --------------------------------------------------------------------------
# The wish wall, and claiming a wish
# --------------------------------------------------------------------------

def list_open_wishes(
    conn: sqlite3.Connection,
    zip_code: str | None = None,
    zip_codes: list[str] | None = None,
    max_cost_usd: float | None = None,
    categories: list[str] | None = None,
    request_type: str | None = None,
    occasion: str | None = None,
    limit: int | None = None,
) -> list[Request]:
    """Open wishes, soonest deadline first, then longest waiting.

    Wishes with no deadline sort after those with one. A wish without a date is
    not urgent and must not be treated as if it were.
    """
    clauses = ["status = ?"]
    params: list = [RequestStatus.OPEN.value]

    if zip_code:
        clauses.append("zip = ?")
        params.append(zip_code)
    if zip_codes:
        clauses.append(f"zip IN ({','.join('?' for _ in zip_codes)})")
        params.extend(zip_codes)
    if categories:
        clauses.append(f"category IN ({','.join('?' for _ in categories)})")
        params.extend(categories)
    if request_type:
        clauses.append("request_type = ?")
        params.append(request_type)
    if occasion:
        clauses.append("occasion = ?")
        params.append(occasion)
    if max_cost_usd is not None:
        # The most this wish could cost: the top of a range, else the estimate.
        clauses.append(
            "COALESCE(budget_max_usd, estimated_cost_usd, budget_min_usd, 0) <= ?"
        )
        params.append(max_cost_usd)

    sql = (
        f"SELECT * FROM requests WHERE {' AND '.join(clauses)} "
        "ORDER BY deadline IS NULL, deadline, created_at"
    )
    if limit is not None:
        sql += " LIMIT ?"
        params.append(limit)

    return [_request(r) for r in conn.execute(sql, params)]


def claim_wish(
    conn: sqlite3.Connection,
    request_id: int,
    donor_alias: str,
    dropoff: date,
    delivery: date,
) -> Pledge | None:
    """Lock a wish to one donor. Returns None if someone got there first.

    The UPDATE carries `AND status = 'open'`, so two donors pressing Grant at
    the same moment cannot both succeed: SQLite applies one, and the other
    changes no rows and is told the wish is gone.
    """
    cur = conn.execute(
        "UPDATE requests SET status = ? WHERE id = ? AND status = ?",
        (RequestStatus.GRANTED.value, request_id, RequestStatus.OPEN.value),
    )
    if cur.rowcount == 0:
        return None

    pledge = Pledge(
        request_id=request_id,
        donor_alias=donor_alias,
        dropoff_date=dropoff,
        delivery_date=delivery,
        status=PledgeStatus.PLEDGED,
    )
    pledge.id = insert_pledge(pledge, conn)
    return pledge


def get_request(conn: sqlite3.Connection, request_id: int) -> Request | None:
    row = conn.execute("SELECT * FROM requests WHERE id = ?", (request_id,)).fetchone()
    return _request(row) if row else None


def get_pledge_for_request(
    conn: sqlite3.Connection, request_id: int
) -> Pledge | None:
    row = conn.execute(
        "SELECT * FROM pledges WHERE request_id = ? ORDER BY id DESC LIMIT 1",
        (request_id,),
    ).fetchone()
    return _pledge(row) if row else None


# --------------------------------------------------------------------------
# The coordinator's run sheet
# --------------------------------------------------------------------------

def pledges_in_week(
    conn: sqlite3.Connection, week_start: date, week_end: date
) -> list[Pledge]:
    """Every pledge whose drop-off OR delivery falls in the week.

    Both, because a drop-off on Thursday and its delivery on Saturday are the
    same week here, but a pledge made late in one week can be delivered in the
    next, and the coordinator needs to see it in both.
    """
    rows = conn.execute(
        """SELECT * FROM pledges
            WHERE (dropoff_date  BETWEEN ? AND ?)
               OR (delivery_date BETWEEN ? AND ?)
            ORDER BY dropoff_date, id""",
        (week_start.isoformat(), week_end.isoformat(),
         week_start.isoformat(), week_end.isoformat()),
    )
    return [_pledge(r) for r in rows]


def get_pledge(conn: sqlite3.Connection, pledge_id: int) -> Pledge | None:
    row = conn.execute("SELECT * FROM pledges WHERE id = ?", (pledge_id,)).fetchone()
    return _pledge(row) if row else None


def set_window_response(
    conn: sqlite3.Connection, pledge_id: int, response: WindowResponse
) -> None:
    conn.execute(
        "UPDATE pledges SET window_response = ? WHERE id = ?",
        (response.value, pledge_id),
    )


# One click on the run sheet moves both the pledge and its wish. A missed
# drop-off is the interesting one: the wish goes back on the wall rather than
# being quietly lost, so another donor can pick it up.
_WISH_STATUS_FOR_PLEDGE = {
    PledgeStatus.PLEDGED: RequestStatus.GRANTED,
    PledgeStatus.DROPPED_OFF: RequestStatus.DROPPED_OFF,
    PledgeStatus.DELIVERED: RequestStatus.DELIVERED,
    PledgeStatus.MISSED: RequestStatus.OPEN,
    PledgeStatus.RELEASED: RequestStatus.OPEN,
    PledgeStatus.CANCELED: RequestStatus.OPEN,
}


def set_pledge_status(
    conn: sqlite3.Connection, pledge_id: int, status: PledgeStatus
) -> Pledge | None:
    """Move a pledge, and move its wish to match."""
    pledge = get_pledge(conn, pledge_id)
    if pledge is None:
        return None

    conn.execute(
        "UPDATE pledges SET status = ? WHERE id = ?", (status.value, pledge_id)
    )
    update_request_status(conn, pledge.request_id, _WISH_STATUS_FOR_PLEDGE[status])
    return get_pledge(conn, pledge_id)


def pledges_for_family(conn: sqlite3.Connection, family_alias: str) -> list[Pledge]:
    """What is on its way to one family."""
    rows = conn.execute(
        """SELECT p.* FROM pledges p
             JOIN requests r ON r.id = p.request_id
            WHERE r.family_alias = ?
            ORDER BY p.delivery_date, p.id""",
        (family_alias,),
    )
    return [_pledge(r) for r in rows]


def recently_granted(
    conn: sqlite3.Connection, since: date, limit: int = 60
) -> list[Request]:
    """Wishes *delivered* since `since`.

    These are the gold leaves: proof on the tree that wishes do get granted,
    which an empty-looking tree of open needs never shows. Granted means it
    reached the neighbor, so a wish someone has claimed but not yet dropped
    off is not gold yet — it is still an open promise.

    Dated on `delivery_date` rather than `created_at`, because the question
    is when the wish arrived, not when the row was written.
    """
    rows = conn.execute(
        """SELECT r.* FROM requests r
             JOIN pledges p ON p.request_id = r.id
            WHERE r.status = ?
              AND p.status = ?
              AND p.delivery_date >= ?
            ORDER BY p.delivery_date DESC
            LIMIT ?""",
        (RequestStatus.DELIVERED.value, PledgeStatus.DELIVERED.value,
         since.isoformat(), limit),
    )
    return [_request(r) for r in rows]


def granted_ever(conn: sqlite3.Connection) -> int:
    """How many wishes have actually reached a neighbor, all time.

    Granted means delivered. A wish someone has claimed, or dropped at the
    hub, is on its way and is not counted yet — the number on the landing
    page is a promise kept, not a promise made.

    Counted on distinct wishes, so one released and granted again by someone
    else counts once. This number is read from the database every time it is
    shown, and it has to be real.
    """
    row = conn.execute(
        """SELECT COUNT(DISTINCT request_id) AS n FROM pledges
            WHERE status = ?""",
        (PledgeStatus.DELIVERED.value,),
    ).fetchone()
    return int(row["n"])
