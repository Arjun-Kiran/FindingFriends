import pytest

from Database import database


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client backed by a throwaway database file."""
    import Main

    db_file = str(tmp_path / "test_game_state.db")
    monkeypatch.setattr(database, "get_database", lambda: db_file)
    database.build_game_state_table()
    Main.app.config['TESTING'] = True
    with Main.app.test_client() as test_client:
        yield test_client


def test_get_game_state_in_db_returns_none_when_missing(tmp_path, monkeypatch):
    db_file = str(tmp_path / "test_game_state.db")
    monkeypatch.setattr(database, "get_database", lambda: db_file)
    database.build_game_state_table()

    assert database.get_game_state_in_db("no-such-game") is None


def test_game_session_returns_404_for_unknown_game(client):
    response = client.get("/game/below-adopt-havoc/player/bb1957b1-fe5d-4f2c-bc57-0e647773437c")

    assert response.status_code == 404
    assert response.get_json()['error'] == 'game_not_found'


def test_game_session_returns_404_for_unknown_player(client):
    game_code = client.get("/create").get_json()['game_code']

    response = client.get(f"/game/{game_code}/player/not-a-real-player")

    assert response.status_code == 404
    assert response.get_json()['error'] == 'player_not_found'


def test_join_returns_404_for_unknown_game(client):
    response = client.get("/join/below-adopt-havoc?nick_name=arjun")

    assert response.status_code == 404
    assert response.get_json()['error'] == 'game_not_found'


def test_join_returns_400_without_nick_name(client):
    game_code = client.get("/create").get_json()['game_code']

    response = client.get(f"/join/{game_code}")

    assert response.status_code == 400
    assert response.get_json()['error'] == 'missing_nick_name'


def test_join_succeeds_for_existing_game(client):
    game_code = client.get("/create").get_json()['game_code']

    response = client.get(f"/join/{game_code}?nick_name=arjun")

    assert response.status_code == 200
    assert response.get_json()['nick_name'] == 'arjun'
