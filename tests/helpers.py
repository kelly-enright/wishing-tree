"""Signing a test client in.

Every per-account endpoint now asks who is calling, so a test that acts as a
neighbor or a wish granter has to log in the way a person would. These do it
with the seeded demo password, through the real login endpoint — no fixture
reaches past it and writes a session row directly, because then the tests
would stop covering the thing most worth covering.
"""

from backend import config, db


def email_for(alias: str) -> str:
    table = "families" if alias.startswith("Neighbor") else "donors"
    with db.connect(config.DB_PATH) as conn:
        row = conn.execute(
            f"SELECT contact_email FROM {table} WHERE alias = ?", (alias,)
        ).fetchone()
    assert row is not None, f"no seeded account for {alias}"
    return row["contact_email"]


def sign_in(client, alias: str):
    """Log this client in as `alias`, replacing whoever it was before."""
    role = "family" if alias.startswith("Neighbor") else "donor"
    response = client.post("/api/auth/login", json={
        "email": email_for(alias), "password": config.DEMO_PASSWORD,
    })
    assert response.status_code == 200, response.text
    if response.json().get("must_choose"):
        chosen = client.post("/api/auth/side", json={"role": role})
        assert chosen.status_code == 200, chosen.text
    return client


def sign_out(client):
    client.post("/api/auth/logout")
    client.cookies.clear()
    return client


def grant_as(client, donor: str, request_id: int, **extra):
    """Grant a wish as `donor`, signing in as them first.

    Several tests need two different granters — a race, a reopened wish, a
    week with more than one drop-off. Before accounts the alias in the body
    was enough; now each of them has to actually be that person.
    """
    sign_in(client, donor)
    return client.post("/api/grant", json={
        "donor_alias": donor, "request_id": request_id, **extra,
    })
