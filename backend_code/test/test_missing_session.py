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


@pytest.fixture
def socket_client(tmp_path, monkeypatch):
    """Socket.IO test client backed by a throwaway database file."""
    import Main

    db_file = str(tmp_path / "test_game_state.db")
    monkeypatch.setattr(database, "get_database", lambda: db_file)
    database.build_game_state_table()
    Main.app.config['TESTING'] = True
    client = Main.socketio.test_client(Main.app)
    yield client
    client.disconnect()


def received_event(client, name: str):
    """The payload of the first `name` event this client received, or None."""
    for message in client.get_received():
        if message['name'] == name:
            return message['args'][0]
    return None


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


def test_socket_join_reports_session_invalid_for_unknown_game(socket_client):
    socket_client.get_received()  # drop the connect handshake

    socket_client.emit('join', {
        'game_code': 'below-adopt-havoc',
        'player_uuid': 'bb1957b1-fe5d-4f2c-bc57-0e647773437c',
    })

    payload = received_event(socket_client, 'session_invalid')
    assert payload is not None
    assert payload['reason'] == 'game_not_found'


def test_socket_join_reports_session_invalid_for_unknown_player(socket_client):
    import Main

    with Main.app.test_client() as http:
        game_code = http.get("/create").get_json()['game_code']
    socket_client.get_received()

    socket_client.emit('join', {'game_code': game_code, 'player_uuid': 'not-a-real-player'})

    payload = received_event(socket_client, 'session_invalid')
    assert payload is not None
    assert payload['reason'] == 'player_not_found'


def test_socket_join_sends_game_state_for_a_real_player(socket_client):
    import Main

    with Main.app.test_client() as http:
        game_code = http.get("/create").get_json()['game_code']
        player_uuid = http.get(f"/join/{game_code}?nick_name=arjun").get_json()['new_player_uuid']
    socket_client.get_received()

    socket_client.emit('join', {'game_code': game_code, 'player_uuid': player_uuid})

    assert received_event(socket_client, 'session_invalid') is None


def test_game_action_on_a_forgotten_game_reports_session_invalid(socket_client):
    socket_client.get_received()

    socket_client.emit('start_game', {
        'game_code': 'below-adopt-havoc',
        'player_uuid': 'bb1957b1-fe5d-4f2c-bc57-0e647773437c',
    })

    payload = received_event(socket_client, 'session_invalid')
    assert payload is not None
    assert payload['reason'] == 'game_not_found'
