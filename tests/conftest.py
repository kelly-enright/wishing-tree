"""Shared test setup."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

from backend import accounts, config


@pytest.fixture(autouse=True)
def fast_hashing(monkeypatch):
    """Hash at bcrypt's minimum cost for the duration of the suite.

    The work factor is the whole point of bcrypt, so lowering it is not
    something to do lightly. It is safe here because nothing in the test
    suite is a real credential: every account is seeded with a published demo
    password into a temporary database that is deleted when the test ends.

    What it buys is the difference between a suite that runs and one nobody
    waits for. Seeding creates 23 accounts, and at cost 12 that is about five
    seconds per test, times three hundred tests.

    The production value lives in `config.BCRYPT_ROUNDS` and is untouched by
    this; `test_accounts.py` asserts that default is still 12.
    """
    monkeypatch.setattr(config, "BCRYPT_ROUNDS", 4)


@pytest.fixture(autouse=True)
def clean_login_throttle():
    """No test inherits another test's failed logins."""
    accounts.reset_throttle()
    yield
    accounts.reset_throttle()
