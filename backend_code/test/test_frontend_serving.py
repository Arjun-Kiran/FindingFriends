"""Serving the built SPA from the same origin as the API.

In production one gunicorn serves the page, the REST endpoints and the socket,
so that a player's browser talks to exactly one origin. That puts a catch-all
route in the app, and the risk a catch-all brings is that it quietly swallows
the API. These tests pin the boundary.
"""
import json

import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    """A test client with a fake frontend build in place."""
    import Main

    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>SPA shell</title>")
    (dist / "assets" / "app-abc123.js").write_text("console.log('built');")

    monkeypatch.setattr(Main, "FRONTEND_DIST", str(dist))
    Main.app.config["TESTING"] = True
    with Main.app.test_client() as c:
        yield c


@pytest.fixture
def client_without_build(tmp_path, monkeypatch):
    """A test client with no build on disk — the development case."""
    import Main

    monkeypatch.setattr(Main, "FRONTEND_DIST", str(tmp_path / "nothing-here"))
    Main.app.config["TESTING"] = True
    with Main.app.test_client() as c:
        yield c


def test_root_serves_the_spa_shell_when_built(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"SPA shell" in response.data


def test_root_says_the_backend_is_alive_when_not_built(client_without_build):
    response = client_without_build.get("/")
    assert response.status_code == 200
    assert b"backend is alive" in response.data


def test_built_asset_is_served(client):
    response = client.get("/assets/app-abc123.js")
    assert response.status_code == 200
    assert b"console.log" in response.data


def test_api_route_is_not_shadowed_by_the_catch_all(client):
    """The whole point of the boundary.

    /create is a static rule and the SPA fallback is /<path:...>. Werkzeug ranks
    the static rule higher regardless of definition order, but that is a
    routing-internals detail this app depends on, so assert it rather than
    trust it: a regression hands players the HTML shell where they expect JSON.
    """
    response = client.get("/create")
    assert response.status_code == 200
    payload = json.loads(response.data)
    assert "game_code" in payload
    assert b"SPA shell" not in response.data


def test_join_route_with_a_parameter_is_not_shadowed(client):
    created = json.loads(client.get("/create").data)
    response = client.get(f"/join/{created['game_code']}")
    # Whatever it answers, it must be the API answering and not the SPA shell.
    assert b"SPA shell" not in response.data


def test_unknown_path_falls_back_to_the_spa(client):
    """A client-side route is not a missing file."""
    response = client.get("/some/deep/client/route")
    assert response.status_code == 200
    assert b"SPA shell" in response.data


def test_index_is_not_cached_but_hashed_assets_are(client):
    """A cached index.html points at asset hashes that no longer exist."""
    assert "no-cache" in client.get("/").headers.get("Cache-Control", "")
    asset_cache = client.get("/assets/app-abc123.js").headers.get("Cache-Control", "")
    assert "immutable" in asset_cache


def test_path_traversal_does_not_escape_the_build(client, tmp_path):
    """send_from_directory resolves through safe_join; confirm it holds."""
    (tmp_path / "secret.txt").write_text("do not serve me")
    response = client.get("/../secret.txt")
    assert b"do not serve me" not in response.data


def test_unknown_path_is_404_when_there_is_no_build(client_without_build):
    """Without a build there is no shell to fall back to."""
    assert client_without_build.get("/some/client/route").status_code == 404
