"""check_play: asking whether a play would be legal without making it.

This is what lets a player pick their answer to a trick before their turn and
queue it. The promise the client relies on is that a play check_play calls
legal is a play play_cards will take, so these drive a real game rather than
the rules helpers, which have tests of their own.
"""
import pytest

# `clients` is a fixture; importing it is what makes it available here.
from test.test_trick_attribution_flow import clients, _started_game, _view, _legal_card  # noqa: F401


def _check(sock, code, uuid, cards, request_id=7):
    """Ask check_play about `cards` and return its one answer."""
    sock.get_received()
    sock.emit('check_play', {
        'game_code': code, 'player_uuid': uuid,
        'cards': [{'suit': c['suit'], 'rank': c['rank']} for c in cards],
        'request_id': request_id,
    })
    received = sock.get_received()
    assert [m for m in received if m['name'] == 'error'] == []
    answers = [m['args'][0] for m in received if m['name'] == 'play_check']
    assert len(answers) == 1
    return answers[0]


def _play(sock, code, uuid, cards):
    sock.get_received()
    sock.emit('play_cards', {
        'game_code': code, 'player_uuid': uuid,
        'cards': [{'suit': c['suit'], 'rank': c['rank']} for c in cards],
    })
    return [m['args'][0]['message'] for m in sock.get_received() if m['name'] == 'error']


def _led_trick(http, sock):
    """A game whose first trick has been led. Returns the code, the leader,
    the player now on turn, and a player further round who has yet to play."""
    code, uuids = _started_game(http, sock)
    leader = _view(http, code, uuids[0])['current_player']['uuid']
    assert _play(sock, code, leader, [_legal_card(_view(http, code, leader))]) == []

    on_turn = _view(http, code, uuids[0])['current_player']['uuid']
    waiting = next(u for u in uuids if u not in (leader, on_turn))
    return code, leader, on_turn, waiting


@pytest.mark.unit
def test_a_legal_follow_is_called_legal_before_the_turn(clients):
    http, sock = clients
    code, _, _, waiting = _led_trick(http, sock)

    answer = _check(sock, code, waiting, [_legal_card(_view(http, code, waiting))])

    assert answer == {'request_id': 7, 'legal': True, 'message': ''}


@pytest.mark.unit
def test_checking_plays_nothing(clients):
    http, sock = clients
    code, _, on_turn, waiting = _led_trick(http, sock)
    before = _view(http, code, waiting)

    _check(sock, code, waiting, [_legal_card(before)])

    after = _view(http, code, waiting)
    assert len(after['cards_in_active_pile']) == 1
    assert after['player_hand'] == before['player_hand']
    assert after['current_player']['uuid'] == on_turn


@pytest.mark.unit
def test_an_illegal_follow_is_explained(clients):
    http, sock = clients
    code, _, _, waiting = _led_trick(http, sock)
    hand = _view(http, code, waiting)['player_hand']

    answer = _check(sock, code, waiting, hand[:2])

    assert answer['legal'] is False
    assert answer['message'] == '1 card was led, so you have to play 1.'


@pytest.mark.unit
def test_nothing_can_be_checked_ahead_of_a_lead(clients):
    """Nobody knows what they are answering until something is led, and a lead
    of top cards is judged against hands that are not the player's own."""
    http, sock = clients
    code, uuids = _started_game(http, sock)
    leader = _view(http, code, uuids[0])['current_player']['uuid']
    other = next(u for u in uuids if u != leader)

    answer = _check(sock, code, other, [_view(http, code, other)['player_hand'][0]])

    assert answer['legal'] is False
    assert 'Nothing has been led' in answer['message']


@pytest.mark.unit
def test_a_player_who_has_played_has_nothing_left_to_check(clients):
    http, sock = clients
    code, leader, _, _ = _led_trick(http, sock)

    answer = _check(sock, code, leader, [_view(http, code, leader)['player_hand'][0]])

    assert answer['legal'] is False
    assert 'already played' in answer['message']


@pytest.mark.unit
def test_a_play_checked_early_is_taken_when_the_turn_arrives(clients):
    """The whole point of queueing: the answer must still hold on the turn."""
    http, sock = clients
    code, _, on_turn, _ = _led_trick(http, sock)
    uuids = [p['uuid'] for p in _view(http, code, on_turn)['player_list']]
    after_that = uuids[(uuids.index(on_turn) + 1) % len(uuids)]

    queued = _legal_card(_view(http, code, after_that))
    assert _check(sock, code, after_that, [queued])['legal'] is True

    assert _play(sock, code, on_turn, [_legal_card(_view(http, code, on_turn))]) == []
    assert _view(http, code, after_that)['my_turn'] is True
    assert _play(sock, code, after_that, [queued]) == []
