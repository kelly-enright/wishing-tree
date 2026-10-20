"""The .env lookup rule the course requires, plus region and allowlist config.

The rule: look in the repo's own folder first, then one level above it. The
teaching staff keep their .env one level up, so the second path is the one that
actually matters when the project is graded.
"""

import pytest

from backend import config


# --------------------------------------------------------------------------
# .env lookup
# --------------------------------------------------------------------------

def _write_env(folder, key_value: str) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / ".env").write_text(f"PORTKEY_API_KEY={key_value}\n")


def test_key_is_found_one_level_above_the_repo(tmp_path, monkeypatch):
    """The staff case: no .env in the repo, one in the parent folder."""
    repo = tmp_path / "wishing-tree"
    repo.mkdir()
    _write_env(tmp_path, "key-from-parent")
    monkeypatch.delenv("PORTKEY_API_KEY", raising=False)

    paths = [repo / ".env", tmp_path / ".env"]
    assert config.require_api_key(paths) == "key-from-parent"


def test_repo_env_beats_the_one_above_it(tmp_path, monkeypatch):
    """Nearest wins: a key in the repo folder overrides the parent's."""
    repo = tmp_path / "wishing-tree"
    _write_env(repo, "key-from-repo")
    _write_env(tmp_path, "key-from-parent")
    monkeypatch.delenv("PORTKEY_API_KEY", raising=False)

    paths = [repo / ".env", tmp_path / ".env"]
    assert config.require_api_key(paths) == "key-from-repo"


def test_missing_key_stops_with_a_message_naming_both_paths(tmp_path, monkeypatch):
    repo = tmp_path / "wishing-tree"
    repo.mkdir()
    monkeypatch.delenv("PORTKEY_API_KEY", raising=False)

    paths = [repo / ".env", tmp_path / ".env"]
    with pytest.raises(RuntimeError) as err:
        config.require_api_key(paths)

    message = str(err.value)
    assert "PORTKEY_API_KEY is not set" in message
    assert str(repo / ".env") in message       # looked in the repo folder
    assert str(tmp_path / ".env") in message   # and one level above it


def test_an_env_file_with_no_key_still_fails(tmp_path, monkeypatch):
    repo = tmp_path / "wishing-tree"
    repo.mkdir()
    (repo / ".env").write_text("PORTKEY_API_KEY=\n")
    monkeypatch.delenv("PORTKEY_API_KEY", raising=False)

    with pytest.raises(RuntimeError):
        config.require_api_key([repo / ".env", tmp_path / ".env"])


def test_api_key_status_does_not_raise(tmp_path, monkeypatch):
    repo = tmp_path / "wishing-tree"
    repo.mkdir()
    monkeypatch.delenv("PORTKEY_API_KEY", raising=False)

    ok, note = config.api_key_status([repo / ".env", tmp_path / ".env"])
    assert ok is False and "PORTKEY_API_KEY" in note


def test_the_real_search_paths_are_repo_then_one_above():
    assert config.ENV_SEARCH_PATHS == [
        config.PROJECT_ROOT / ".env",
        config.PROJECT_ROOT.parent / ".env",
    ]


# --------------------------------------------------------------------------
# Region configuration
# --------------------------------------------------------------------------

def test_new_haven_is_the_seeded_active_region():
    region = config.get_region("new_haven")
    assert region.active
    assert region.name == "New Haven, CT"
    assert region.hub_name == "Yale School of Management"
    assert "165 Whitney Ave" in region.hub_address
    assert region.dropoff_window.label() == "Thursday 4:00 PM-7:00 PM"
    assert region.delivery_window.label() == "Saturday 10:00 AM-1:00 PM"


def test_zip_lookup_finds_the_region():
    assert config.region_for_zip("06511") is not None
    assert config.region_for_zip("90210") is None


def test_unknown_region_slug_raises():
    with pytest.raises(KeyError):
        config.get_region("atlantis")


# --------------------------------------------------------------------------
# Retailer allowlist
# --------------------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "https://www.target.com/p/kids-puffer-jacket/-/A-88204117",
    "https://amazon.com/dp/B0CT7QKMN4",
    "https://shop.oldnavy.com/anything",
])
def test_allowlisted_links_pass(url):
    assert config.is_allowed_retailer(url)


@pytest.mark.parametrize("url", [
    None,
    "",
    "http://www.target.com/p/x",              # not https
    "https://target.com.evil.example/p/x",    # lookalike host
    "https://evil.example/target.com",        # allowlisted name only in the path
    "https://user@target.com/p/x",            # embedded credentials
    "javascript:alert(1)",
])
def test_everything_else_is_rejected(url):
    assert not config.is_allowed_retailer(url)


# --------------------------------------------------------------------------
# Prices
# --------------------------------------------------------------------------

def test_prices_are_still_marked_as_placeholders():
    """Guards the report: a placeholder price must never read as a real cost."""
    assert config.PRICES_ARE_PLACEHOLDERS is True
    assert config.estimate_cost_usd(1000, 1000, 1000) == 0.0
