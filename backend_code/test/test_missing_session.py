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
    if client.is_connected():
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


def test_disconnect_mid_game_holds_the_seat(socket_client, monkeypatch):
    """A player who drops mid-game keeps their seat and hand — the round
    depends on both — and shows up as disconnected to everyone else."""
    import Main
    from Game.Modules.EventEnum import GameEventState

    with Main.app.test_client() as http:
        game_code = http.get("/create").get_json()['game_code']
        uuids = [
            http.get(f"/join/{game_code}?nick_name=p{i}").get_json()['new_player_uuid']
            for i in range(5)
        ]

    gs = Main.get_redis_cache(game_code)
    gs.game_event_state = GameEventState.ROUND_STARTED
    Main.upsert_game_state_in_db(game_code, gs.model_dump(mode='json'), True)

    socket_client.emit('join', {'game_code': game_code, 'player_uuid': uuids[0]})
    socket_client.disconnect()

    reloaded = Main.get_redis_cache(game_code)
    assert uuids[0] in reloaded.player_dict
    assert len(reloaded.player_order) == 5


def test_disconnect_in_lobby_still_removes_the_player(socket_client):
    """The lobby keeps its old behaviour: nothing is dealt yet, so a player who
    leaves before the game starts frees up their spot."""
    import Main

    with Main.app.test_client() as http:
        game_code = http.get("/create").get_json()['game_code']
        first = http.get(f"/join/{game_code}?nick_name=alice").get_json()['new_player_uuid']
        http.get(f"/join/{game_code}?nick_name=bob")

    socket_client.emit('join', {'game_code': game_code, 'player_uuid': first})
    socket_client.disconnect()

    reloaded = Main.get_redis_cache(game_code)
    assert first not in reloaded.player_dict


def test_player_view_marks_players_without_a_socket_as_disconnected():
    from Game.Components.GameState import GameState
    from Game.Systems.GameStateSystem import add_player, generate_player
    from Game.Views.PlayerView import player_view_state

    gs = GameState()
    gs.game_code = 'below-adopt-havoc'
    alice = generate_player(name='alice')
    bob = generate_player(name='bob')
    add_player(gs, alice)
    add_player(gs, bob)

    view = player_view_state(gs, str(alice.uuid), connected_uuids={str(alice.uuid)})

    assert view.disconnected_players == [str(bob.uuid)]


def test_player_view_assumes_everyone_is_present_when_not_told():
    from Game.Components.GameState import GameState
    from Game.Systems.GameStateSystem import add_player, generate_player
    from Game.Views.PlayerView import player_view_state

    gs = GameState()
    gs.game_code = 'below-adopt-havoc'
    alice = generate_player(name='alice')
    add_player(gs, alice)

    view = player_view_state(gs, str(alice.uuid))

    assert view.disconnected_players == []


def test_disconnect_mid_game_announces_it_to_the_table(socket_client):
    """The other players are told, not left to infer it from a turn that never
    comes."""
    import Main
    from Game.Modules.EventEnum import Event, GameEventState

    with Main.app.test_client() as http:
        game_code = http.get("/create").get_json()['game_code']
        uuids = [
            http.get(f"/join/{game_code}?nick_name=p{i}").get_json()['new_player_uuid']
            for i in range(5)
        ]

    gs = Main.get_redis_cache(game_code)
    gs.game_event_state = GameEventState.ROUND_STARTED
    Main.upsert_game_state_in_db(game_code, gs.model_dump(mode='json'), True)

    socket_client.emit('join', {'game_code': game_code, 'player_uuid': uuids[0]})
    socket_client.disconnect()

    reloaded = Main.get_redis_cache(game_code)
    assert reloaded.events[-1].event == Event.PLAYER_DISCONNECTED
    assert 'p0' in reloaded.events[-1].message


def test_rejoining_mid_game_announces_the_return(socket_client):
    import Main
    from Game.Modules.EventEnum import Event, GameEventState

    with Main.app.test_client() as http:
        game_code = http.get("/create").get_json()['game_code']
        player_uuid = http.get(f"/join/{game_code}?nick_name=alice").get_json()['new_player_uuid']

    gs = Main.get_redis_cache(game_code)
    gs.game_event_state = GameEventState.ROUND_STARTED
    Main.upsert_game_state_in_db(game_code, gs.model_dump(mode='json'), True)

    socket_client.emit('join', {'game_code': game_code, 'player_uuid': player_uuid})

    reloaded = Main.get_redis_cache(game_code)
    assert reloaded.events[-1].event == Event.PLAYER_RECONNECTED
    assert 'alice' in reloaded.events[-1].message


def test_joining_the_lobby_is_not_reported_as_a_reconnect(socket_client):
    """In the lobby every join is a first join — announcing a 'reconnect' there
    would be a lie."""
    import Main
    from Game.Modules.EventEnum import Event

    with Main.app.test_client() as http:
        game_code = http.get("/create").get_json()['game_code']
        player_uuid = http.get(f"/join/{game_code}?nick_name=alice").get_json()['new_player_uuid']

    socket_client.emit('join', {'game_code': game_code, 'player_uuid': player_uuid})

    reloaded = Main.get_redis_cache(game_code)
    assert all(e.event != Event.PLAYER_RECONNECTED for e in reloaded.events)


def test_a_second_socket_for_the_same_player_is_not_a_reconnect(socket_client):
    """A player with two tabs open is still present; the extra socket must not
    announce a return."""
    import Main
    from Game.Modules.EventEnum import Event, GameEventState

    with Main.app.test_client() as http:
        game_code = http.get("/create").get_json()['game_code']
        player_uuid = http.get(f"/join/{game_code}?nick_name=alice").get_json()['new_player_uuid']

    gs = Main.get_redis_cache(game_code)
    gs.game_event_state = GameEventState.ROUND_STARTED
    Main.upsert_game_state_in_db(game_code, gs.model_dump(mode='json'), True)

    socket_client.emit('join', {'game_code': game_code, 'player_uuid': player_uuid})
    second_tab = Main.socketio.test_client(Main.app)
    second_tab.emit('join', {'game_code': game_code, 'player_uuid': player_uuid})

    reloaded = Main.get_redis_cache(game_code)
    reconnects = [e for e in reloaded.events if e.event == Event.PLAYER_RECONNECTED]
    assert len(reconnects) == 1  # only the first join, which was a real return
    second_tab.disconnect()


def test_events_are_capped_so_a_flapping_connection_cannot_grow_forever():
    from Game.Components.GameState import GameState
    from Game.Modules.EventEnum import Event
    from Game.Systems.EventSystem import MAX_EVENTS, record_event

    gs = GameState()
    for i in range(MAX_EVENTS + 25):
        record_event(gs, Event.PLAYER_DISCONNECTED, f'event {i}')

    assert len(gs.events) == MAX_EVENTS
    assert gs.events[-1].message == f'event {MAX_EVENTS + 24}'  # newest kept
