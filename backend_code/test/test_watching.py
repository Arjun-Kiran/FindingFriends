"""HR-8: watching a game.

A watcher is shown the table and nothing more — no hand, and nothing the
players at the table are not also shown — and cannot act in the game.
"""
import json

import pytest

from Database import database
from Game.Components.Card import Card
from Game.Components.GameState import GameState
from Game.Modules.CardConstants import Rank, Suit
from Game.Modules.EventEnum import GameEventState
from Game.Systems.GameStateSystem import add_player, generate_player, set_player_as_alpha
from Game.Systems.SeatSystem import add_watcher
from Game.Views.PlayerView import watcher_view_state
from test.seats import TableSockets, token_for, view
from test.test_trick_attribution_flow import _legal_card, _started_game


@pytest.fixture
def clients(tmp_path, monkeypatch):
    import Main

    db_file = str(tmp_path / "test_game_state.db")
    monkeypatch.setattr(database, "get_database", lambda: db_file)
    database.build_game_state_table()
    Main.app.config['TESTING'] = True

    with Main.app.test_client() as http:
        table = TableSockets()
        yield http, table
        table.disconnect()


def _named(received, name):
    return [message['args'][0] for message in received if message['name'] == name]


def _table_of_five():
    gs = GameState()
    gs.game_code = 'below-adopt-havoc'
    players = [generate_player(name=name) for name in ('Ann', 'Bob', 'Cal', 'Dee', 'Eve')]
    for player in players:
        add_player(gs, player)
    return gs, [str(player.uuid) for player in players]


@pytest.mark.unit
def test_anyone_with_the_code_can_watch_a_game_under_way(clients):
    http, sock = clients
    code, _ = _started_game(http, sock)

    wes = sock.watch(http, code, 'Wes')

    watching = view(http, code, wes)
    assert watching['is_watcher'] is True
    assert watching['name'] == 'Wes'
    assert watching['game_event_state'] == 'round-started'
    assert len(watching['player_list']) == 5


@pytest.mark.unit
def test_joining_to_play_mid_game_is_still_refused(clients):
    http, sock = clients
    code, _ = _started_game(http, sock)

    response = http.get(f"/join/{code}?nick_name=Wes")

    assert response.status_code == 409


@pytest.mark.unit
def test_a_lobby_can_be_watched_too(clients):
    http, sock = clients
    code = http.get("/create").get_json()['game_code']
    sock.seat(http, code, 'Ann')

    wes = sock.watch(http, code, 'Wes')

    watching = view(http, code, wes)
    assert watching['is_watcher'] is True
    assert watching['game_event_state'] == 'waiting-for-player-to-join'


@pytest.mark.unit
def test_a_watcher_sees_the_table_but_no_hand(clients):
    http, sock = clients
    code, uuids = _started_game(http, sock)
    wes = sock.watch(http, code, 'Wes')

    player = view(http, code, uuids[0])
    watching = view(http, code, wes)

    assert player['player_hand']
    assert watching['player_hand'] == []
    assert watching['playable_hand_cards'] == []
    assert watching['my_turn'] is False
    assert watching['is_alpha'] is False
    assert watching['hosting'] is False
    assert watching['on_alpha_team'] is False
    assert watching['cards_in_active_pile'] == player['cards_in_active_pile']
    assert watching['player_list'] == player['player_list']


@pytest.mark.unit
def test_the_kitty_is_never_shown_to_a_watcher():
    """Not while the alpha sorts it, which is when a player's view carries it."""
    gs, uuids = _table_of_five()
    gs.game_event_state = GameEventState.WAITING_ON_ALPHA_KITTY_SORT
    set_player_as_alpha(gs, uuids[0])
    gs.cards_in_deck = [Card(rank=Rank.ACE, suit=Suit.SPADE)]
    watcher, _ = add_watcher(gs, 'Wes', 0.0)

    watching = watcher_view_state(gs, watcher.uuid)

    assert watching.player_hand == []
    assert watching.kitty_cards == []


@pytest.mark.unit
def test_hidden_totals_are_hidden_from_watchers_too():
    """A watcher who could see them could tell a player."""
    gs, uuids = _table_of_five()
    gs.settings.hide_scores_until_round_end = True
    gs.game_event_state = GameEventState.ROUND_STARTED
    gs.players_round_score = {uuids[1]: 45}
    watcher, _ = add_watcher(gs, 'Wes', 0.0)

    watching = watcher_view_state(gs, watcher.uuid)

    assert watching.scores_hidden is True
    assert watching.players_round_score == {}
    assert watching.defender_team_points == 0


@pytest.mark.unit
def test_a_watcher_is_sent_the_game_as_it_moves(clients):
    http, sock = clients
    code, uuids = _started_game(http, sock)
    wes = sock.watch(http, code, 'Wes')
    sock.get_received()

    leader = view(http, code, uuids[0])['current_player']['uuid']
    card = _legal_card(view(http, code, leader))
    sock.emit('play_cards', {'game_code': code, 'player_uuid': leader,
                             'cards': [{'suit': card['suit'], 'rank': card['rank']}]})

    stats = _named(sock.socket_of(wes).get_received(), 'game_stats')
    assert stats
    assert stats[-1]['is_watcher'] is True
    assert stats[-1]['player_hand'] == []
    assert len(stats[-1]['cards_in_active_pile']) == 1


@pytest.mark.unit
def test_the_table_can_see_who_is_watching(clients):
    http, sock = clients
    code, uuids = _started_game(http, sock)

    sock.watch(http, code, 'Wes')

    player = view(http, code, uuids[0])
    assert [watcher['name'] for watcher in player['watchers']] == ['Wes']
    assert 'Wes is watching' in [event['message'] for event in player['events']]


@pytest.mark.unit
def test_a_watcher_cannot_play(clients):
    """Refused, but not sent home — they are welcome to go on watching."""
    http, sock = clients
    code, uuids = _started_game(http, sock)
    wes = sock.watch(http, code, 'Wes')
    watcher = sock.socket_of(wes)
    watcher.get_received()
    card = view(http, code, uuids[0])['player_hand'][0]

    watcher.emit('play_cards', {'game_code': code,
                                'cards': [{'suit': card['suit'], 'rank': card['rank']}]})

    received = watcher.get_received()
    assert [error['message'] for error in _named(received, 'error')] == [
        'You are watching this game. Ask the host for a seat to play.']
    assert _named(received, 'session_invalid') == []
    assert view(http, code, uuids[0])['cards_in_active_pile'] == []


@pytest.mark.unit
def test_a_watcher_who_leaves_is_gone(clients):
    http, sock = clients
    code, uuids = _started_game(http, sock)
    wes = sock.watch(http, code, 'Wes')
    token = token_for(wes)

    sock.emit('leave_game', {'game_code': code, 'player_uuid': wes})

    assert http.get(f"/game/{code}/player", headers={'X-Player-Token': token}).status_code == 404
    assert view(http, code, uuids[0])['watchers'] == []


@pytest.mark.unit
def test_a_watcher_can_leave_a_lobby(clients):
    http, sock = clients
    code = http.get("/create").get_json()['game_code']
    ann = sock.seat(http, code, 'Ann')
    wes = sock.watch(http, code, 'Wes')

    sock.emit('leave_lobby', {'game_code': code, 'player_uuid': wes})

    assert view(http, code, ann)['watchers'] == []
    assert len(view(http, code, ann)['player_list']) == 1


@pytest.mark.unit
def test_a_watcher_who_disconnects_takes_their_offer_with_them(clients):
    """Nobody should be handed a seat they are not there to play."""
    http, sock = clients
    code, uuids = _started_game(http, sock)
    wes = sock.watch(http, code, 'Wes')
    sock.socket_of(uuids[1]).disconnect()
    sock.emit('volunteer_for_seat', {'game_code': code, 'player_uuid': wes, 'seat_uuid': uuids[1]})
    assert view(http, code, uuids[0])['seat_requests']

    sock.socket_of(wes).disconnect()

    player = view(http, code, uuids[0])
    assert player['seat_requests'] == []
    assert player['watchers'] == []


@pytest.mark.unit
def test_no_watcher_token_reaches_a_screen(clients):
    http, sock = clients
    code, uuids = _started_game(http, sock)
    wes = sock.watch(http, code, 'Wes')

    sent = json.dumps([message['args'] for message in sock.get_received()])
    sent += json.dumps([view(http, code, uuid) for uuid in [*uuids, wes]])

    assert token_for(wes) not in sent


@pytest.mark.unit
def test_a_finished_game_cannot_be_watched(clients):
    import Main

    http, sock = clients
    code, _ = _started_game(http, sock)
    gs = Main.get_redis_cache(code)
    gs.game_event_state = GameEventState.GAME_ENDED
    Main.update_redis_cache(gs)

    assert http.get(f"/watch/{code}?nick_name=Wes").status_code == 409
