"""What Main.game_handler does for every socket handler built on it."""
import pytest

from Database import database
from test.seats import TableSockets


@pytest.fixture
def app_clients(tmp_path, monkeypatch):
    """An HTTP client and a Socket.IO client over one throwaway database."""
    import Main

    db_file = str(tmp_path / "test_game_state.db")
    monkeypatch.setattr(database, "get_database", lambda: db_file)
    database.build_game_state_table()
    Main.app.config['TESTING'] = True

    with Main.app.test_client() as http_client:
        socket_client = TableSockets()
        yield http_client, socket_client
        if socket_client.is_connected():
            socket_client.disconnect()


def _errors(socket_client):
    return [message['args'][0]['message'] for message in socket_client.get_received()
            if message['name'] == 'error']


@pytest.mark.unit
def test_a_crash_is_logged_but_not_shown_to_the_player(app_clients, monkeypatch):
    """The player is told it failed, never the Python error behind it."""
    import Main

    http_client, socket_client = app_clients
    game_code = http_client.get("/create").get_json()['game_code']
    ann = socket_client.seat(http_client, game_code, 'Ann')
    socket_client.get_received()

    def broken(*args, **kwargs):
        raise RuntimeError('internal detail nobody should see')
    monkeypatch.setattr(Main, 'set_player_avatar', broken)

    socket_client.emit('choose_avatar', {'game_code': game_code, 'player_uuid': ann, 'avatar': '🐼'})

    errors = _errors(socket_client)
    assert errors == ['Something went wrong — try that again.']


@pytest.mark.unit
def test_a_payload_that_is_not_an_object_is_refused_politely(app_clients):
    _, socket_client = app_clients

    socket_client.socket_of('').emit('choose_avatar', 'not a dict')

    assert _errors(socket_client) == ['missing game_code']


@pytest.mark.unit
def test_a_refusal_reaches_the_player_word_for_word(app_clients):
    http_client, socket_client = app_clients
    game_code = http_client.get("/create").get_json()['game_code']
    ann = socket_client.seat(http_client, game_code, 'Ann')
    socket_client.get_received()

    socket_client.emit('choose_avatar', {'game_code': game_code, 'player_uuid': ann,
                                         'avatar': 'not an avatar'})

    assert _errors(socket_client) == ['That avatar is not available']
