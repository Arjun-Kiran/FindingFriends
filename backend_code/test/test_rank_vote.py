"""HR-13: the host may put next round's trump rank to a vote.

Optional and per round — a table that never opens one plays exactly as before,
and nobody's level moves either way.
"""
import pytest

from Database import database
from Game.Components.Card import Card
from Game.Modules.CardConstants import Rank, Suit
from Game.Modules.EventEnum import GameEventState
from test.seats import TableSockets, view

NAMES = ('Ann', 'Bob', 'Cal', 'Dee')


@pytest.fixture
def clients(tmp_path, monkeypatch):
    import Main

    monkeypatch.setattr(database, "get_database", lambda: str(tmp_path / "rank_vote.db"))
    database.build_game_state_table()
    Main.app.config['TESTING'] = True

    with Main.app.test_client() as http_client:
        socket_client = TableSockets()
        yield http_client, socket_client
        if socket_client.is_connected():
            socket_client.disconnect()


def _errors(sock):
    return [m['args'][0]['message'] for m in sock.get_received() if m['name'] == 'error']


def _round_ended_table(http, sock, **settings):
    import Main

    code = http.get("/create").get_json()['game_code']
    uuids = [sock.seat(http, code, name) for name in NAMES]
    sock.emit('join', {'game_code': code, 'player_uuid': uuids[0]})
    if settings:
        sock.emit('update_settings', {'game_code': code, 'player_uuid': uuids[0],
                                      'settings': settings})
    sock.emit('start_game', {'game_code': code, 'player_uuid': uuids[0]})
    sock.get_received()
    gs = Main.get_redis_cache(code)
    gs.game_event_state = GameEventState.ROUND_ENDED
    Main.update_redis_cache(gs)
    return code, uuids


def _emit(sock, event, code, uuid, **data):
    sock.emit(event, {'game_code': code, 'player_uuid': uuid, **data})


def _state(code):
    import Main

    return Main.get_redis_cache(code)


@pytest.mark.unit
def test_no_vote_is_open_by_default(clients):
    http, sock = clients
    code, uuids = _round_ended_table(http, sock)

    seen = view(http, code, uuids[1])
    assert seen['rank_proposal'] == 0
    assert seen['rank_override'] == 0


@pytest.mark.unit
def test_only_the_host_can_propose(clients):
    http, sock = clients
    code, uuids = _round_ended_table(http, sock)

    _emit(sock, 'propose_rank', code, uuids[1], rank='KING')

    assert _errors(sock) == ['Only the host can propose a rank']
    assert _state(code).rank_proposal is None


@pytest.mark.unit
def test_a_proposal_counts_the_host_as_a_yes(clients):
    http, sock = clients
    code, uuids = _round_ended_table(http, sock)

    _emit(sock, 'propose_rank', code, uuids[0], rank='KING')

    seen = view(http, code, uuids[1])
    assert seen['rank_proposal'] == Rank.KING.value
    assert (seen['rank_vote_yes'], seen['rank_vote_of']) == (1, 4)


@pytest.mark.unit
def test_a_strict_majority_passes_it(clients):
    """Four seated, so the host plus two more is three of four."""
    http, sock = clients
    code, uuids = _round_ended_table(http, sock)
    _emit(sock, 'propose_rank', code, uuids[0], rank='KING')

    _emit(sock, 'vote_rank', code, uuids[1], approve=True)
    assert _state(code).next_round_rank is None
    _emit(sock, 'vote_rank', code, uuids[2], approve=True)

    gs = _state(code)
    assert gs.next_round_rank == Rank.KING.value
    assert gs.rank_proposal is None
    assert _errors(sock) == []


@pytest.mark.unit
def test_a_tie_stays_open_until_the_host_cancels(clients):
    http, sock = clients
    code, uuids = _round_ended_table(http, sock)
    _emit(sock, 'propose_rank', code, uuids[0], rank='KING')

    _emit(sock, 'vote_rank', code, uuids[1], approve=True)
    _emit(sock, 'vote_rank', code, uuids[2], approve=False)
    _emit(sock, 'vote_rank', code, uuids[3], approve=False)

    gs = _state(code)
    assert gs.rank_proposal == Rank.KING.value
    assert gs.next_round_rank is None

    _emit(sock, 'cancel_rank_vote', code, uuids[0])
    assert _state(code).rank_proposal is None


@pytest.mark.unit
def test_a_vote_can_be_changed(clients):
    http, sock = clients
    code, uuids = _round_ended_table(http, sock)
    _emit(sock, 'propose_rank', code, uuids[0], rank='KING')

    _emit(sock, 'vote_rank', code, uuids[1], approve=False)
    _emit(sock, 'vote_rank', code, uuids[1], approve=True)

    assert view(http, code, uuids[1])['my_rank_vote'] is True


@pytest.mark.unit
def test_the_host_cannot_vote_again(clients):
    http, sock = clients
    code, uuids = _round_ended_table(http, sock)
    _emit(sock, 'propose_rank', code, uuids[0], rank='KING')

    _emit(sock, 'vote_rank', code, uuids[0], approve=True)

    assert 'already counts' in _errors(sock)[0]


@pytest.mark.unit
def test_voting_with_nothing_proposed_is_refused(clients):
    http, sock = clients
    code, uuids = _round_ended_table(http, sock)

    _emit(sock, 'vote_rank', code, uuids[1], approve=True)

    assert _errors(sock) == ['There is no rank vote open.']


@pytest.mark.unit
def test_the_next_round_cannot_start_while_a_vote_is_open(clients):
    http, sock = clients
    code, uuids = _round_ended_table(http, sock)
    _emit(sock, 'propose_rank', code, uuids[0], rank='KING')

    _emit(sock, 'next_round', code, uuids[0])

    assert 'rank vote is still open' in _errors(sock)[0]
    assert _state(code).game_event_state == GameEventState.ROUND_ENDED


@pytest.mark.unit
def test_a_bad_rank_is_refused(clients):
    http, sock = clients
    code, uuids = _round_ended_table(http, sock)

    _emit(sock, 'propose_rank', code, uuids[0], rank='JOKER')

    assert 'Not a rank' in _errors(sock)[0]


@pytest.mark.unit
def test_a_vote_is_refused_mid_round(clients):
    http, sock = clients
    code, uuids = _round_ended_table(http, sock)
    gs = _state(code)
    gs.game_event_state = GameEventState.ROUND_STARTED
    import Main
    Main.update_redis_cache(gs)

    _emit(sock, 'propose_rank', code, uuids[0], rank='KING')

    assert _state(code).rank_proposal is None
    assert _errors(sock) == ['A rank vote can only be opened between rounds']


@pytest.mark.unit
def test_a_passed_rank_binds_the_next_alpha_once_and_moves_no_one(clients):
    http, sock = clients
    code, uuids = _round_ended_table(http, sock)
    levels = dict(_state(code).player_levels)
    _emit(sock, 'propose_rank', code, uuids[0], rank='KING')
    _emit(sock, 'vote_rank', code, uuids[1], approve=True)
    _emit(sock, 'vote_rank', code, uuids[2], approve=True)

    _emit(sock, 'next_round', code, uuids[0])
    assert _errors(sock) == []
    alpha = view(http, code, uuids[0])['alpha_uuid']
    assert view(http, code, alpha)['rank_override'] == Rank.KING.value
    assert _state(code).next_round_rank is None

    _emit(sock, 'declare_trump', code, alpha, suit='HEART', rank='TWO')
    assert 'voted rank' in _errors(sock)[0]

    import Main
    gs = _state(code)
    gs.players_and_hand[alpha] = [Card(rank=Rank.KING, suit=Suit.HEART)]
    Main.update_redis_cache(gs)
    _emit(sock, 'declare_trump', code, alpha, suit='HEART', rank='KING')
    assert _errors(sock) == []
    gs = _state(code)
    assert gs.declare_trump.rank == Rank.KING
    assert gs.round_rank_override is None
    assert gs.player_levels == levels


@pytest.mark.unit
def test_without_a_vote_the_alpha_declares_their_own_level(clients):
    http, sock = clients
    code, uuids = _round_ended_table(http, sock)

    _emit(sock, 'next_round', code, uuids[0])

    alpha = view(http, code, uuids[0])['alpha_uuid']
    assert view(http, code, alpha)['rank_override'] == 0
    _emit(sock, 'declare_trump', code, alpha, suit='HEART', rank='KING')
    assert 'your own level' in _errors(sock)[0]


@pytest.mark.unit
def test_cancelling_drops_a_rank_the_table_already_passed(clients):
    http, sock = clients
    code, uuids = _round_ended_table(http, sock)
    _emit(sock, 'propose_rank', code, uuids[0], rank='KING')
    _emit(sock, 'vote_rank', code, uuids[1], approve=True)
    _emit(sock, 'vote_rank', code, uuids[2], approve=True)

    _emit(sock, 'cancel_rank_vote', code, uuids[0])
    _emit(sock, 'next_round', code, uuids[0])

    alpha = view(http, code, uuids[0])['alpha_uuid']
    assert view(http, code, alpha)['rank_override'] == 0


@pytest.mark.unit
def test_a_table_with_free_trump_choice_has_no_rank_to_vote_on(clients):
    http, sock = clients
    code, uuids = _round_ended_table(http, sock, free_trump_choice=True)

    _emit(sock, 'propose_rank', code, uuids[0], rank='KING')

    assert 'any trump' in _errors(sock)[0]
