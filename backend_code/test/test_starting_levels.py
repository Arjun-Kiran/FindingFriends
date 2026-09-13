"""Starting levels the host can set in the lobby.

For a table picking up a game it did not finish in one sitting. Levels travel
as Rank enum values — 1 is Two, 13 is Ace.
"""
import pytest

from Game.Modules.CardConstants import Rank
# `clients` is a fixture; importing it is what makes it available here.
from test.test_game_settings import clients, _view, _errors, _lobby, _start  # noqa: F401


def _set_level(sock, code, host, target, level):
    sock.emit('set_starting_level', {
        'game_code': code, 'player_uuid': host,
        'target_uuid': target, 'level': level,
    })


@pytest.mark.unit
def test_everyone_starts_on_two_by_default(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)

    levels = _view(http, code, uuids[0])['player_levels']

    assert levels == {uuid: Rank.TWO.value for uuid in uuids}


@pytest.mark.unit
def test_the_host_can_move_a_players_starting_level(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)

    _set_level(sock, code, uuids[0], uuids[1], Rank.SEVEN.value)

    assert _errors(sock) == []
    view = _view(http, code, uuids[1])
    assert view['player_levels'][uuids[1]] == Rank.SEVEN.value
    assert view['my_level'] == Rank.SEVEN.value
    assert _view(http, code, uuids[0])['player_levels'][uuids[2]] == Rank.TWO.value


@pytest.mark.unit
def test_the_whole_table_is_told(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)

    _set_level(sock, code, uuids[0], uuids[1], Rank.KING.value)

    events = _view(http, code, uuids[2])['events']
    assert events[-1]['event'] == 'starting-level-set'
    assert events[-1]['message'] == 'Bob will start on level K'
    assert events[-1]['player_uuid'] == uuids[1]


@pytest.mark.unit
def test_the_level_carries_into_the_game(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)

    _set_level(sock, code, uuids[0], uuids[0], Rank.ACE.value)
    _set_level(sock, code, uuids[0], uuids[3], Rank.FIVE.value)
    _start(sock, code, uuids[0])

    assert _errors(sock) == []
    view = _view(http, code, uuids[0])
    assert view['game_event_state'] != 'waiting-for-player-to-join'
    assert view['my_level'] == Rank.ACE.value
    assert view['player_levels'][uuids[3]] == Rank.FIVE.value


@pytest.mark.unit
def test_a_guest_cannot_set_levels(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)

    _set_level(sock, code, uuids[1], uuids[1], Rank.ACE.value)

    assert _errors(sock) == ['Only the host can change starting levels']
    assert _view(http, code, uuids[1])['my_level'] == Rank.TWO.value


@pytest.mark.unit
def test_levels_are_fixed_once_the_game_starts(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)
    _start(sock, code, uuids[0])
    sock.get_received()

    _set_level(sock, code, uuids[0], uuids[1], Rank.ACE.value)

    assert _errors(sock) == ['Starting levels can only be changed in the lobby']
    assert _view(http, code, uuids[1])['my_level'] == Rank.TWO.value


@pytest.mark.unit
@pytest.mark.parametrize('level', [0, 14, Rank.JOKER.value, '7', True, None])
def test_only_two_to_ace_is_a_level(clients, level):
    http, sock = clients
    code, uuids = _lobby(http, sock)

    _set_level(sock, code, uuids[0], uuids[1], level)

    assert _errors(sock) == ['A starting level has to be a rank from Two to Ace']
    assert _view(http, code, uuids[1])['my_level'] == Rank.TWO.value


@pytest.mark.unit
def test_a_player_not_in_the_game_cannot_be_given_a_level(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)

    _set_level(sock, code, uuids[0], 'not-a-player', Rank.ACE.value)

    assert _errors(sock) == ['That player is not in this game']
