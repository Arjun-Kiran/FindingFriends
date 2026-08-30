"""House rules the host can change in the lobby.

Each setting is a permission: off, the game plays as ZhaoPengyou_Rules.md
describes it; on, one rule is loosened. So each is checked twice — that the
standard rule bites by default, and that turning the setting on lifts it.
"""
import pytest

from Database import database
from Game.Components.Card import Card
from Game.Components.GameState import GameSettings
from Game.Modules.CardConstants import Rank, Suit


@pytest.fixture
def clients(tmp_path, monkeypatch):
    import Main

    db_file = str(tmp_path / "test_game_state.db")
    monkeypatch.setattr(database, "get_database", lambda: db_file)
    database.build_game_state_table()
    Main.app.config['TESTING'] = True

    with Main.app.test_client() as http_client:
        socket_client = Main.socketio.test_client(Main.app)
        yield http_client, socket_client
        if socket_client.is_connected():
            socket_client.disconnect()


def _view(http, code, uuid):
    return http.get(f"/game/{code}/player/{uuid}").get_json()


def _errors(sock):
    return [m['args'][0]['message'] for m in sock.get_received() if m['name'] == 'error']


def _lobby(http, sock):
    """Five players in a lobby, host first, nothing configured yet."""
    code = http.get("/create").get_json()['game_code']
    uuids = [
        http.get(f"/join/{code}?nick_name={name}").get_json()['new_player_uuid']
        for name in ('Ann', 'Bob', 'Cal', 'Dee', 'Eve')
    ]
    sock.emit('join', {'game_code': code, 'player_uuid': uuids[0]})
    sock.get_received()
    return code, uuids


def _configure(sock, code, uuid, **settings):
    sock.emit('update_settings', {
        'game_code': code, 'player_uuid': uuid, 'settings': settings,
    })


def _start(sock, code, host):
    sock.emit('start_game', {'game_code': code, 'player_uuid': host})


def _level_of(http, code, uuid):
    return _view(http, code, uuid)['my_level']


# --- the settings themselves ---

@pytest.mark.unit
def test_a_table_nobody_configures_plays_the_standard_game():
    assert GameSettings() == GameSettings(
        trumps_can_be_called=False,
        free_trump_choice=False,
        random_first_alpha=False,
    )


@pytest.mark.unit
def test_the_host_can_change_a_rule(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)

    _configure(sock, code, uuids[0], free_trump_choice=True)

    assert _errors(sock) == []
    assert _view(http, code, uuids[0])['settings']['free_trump_choice'] is True


@pytest.mark.unit
def test_the_whole_table_can_see_what_they_are_playing(clients):
    """Not just the host — everyone has to know what game they are in."""
    http, sock = clients
    code, uuids = _lobby(http, sock)

    _configure(sock, code, uuids[0], trumps_can_be_called=True)

    assert _view(http, code, uuids[3])['settings']['trumps_can_be_called'] is True


@pytest.mark.unit
def test_a_setting_left_out_keeps_the_value_it_had(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)
    _configure(sock, code, uuids[0], free_trump_choice=True)

    _configure(sock, code, uuids[0], random_first_alpha=True)

    settings = _view(http, code, uuids[0])['settings']
    assert settings['free_trump_choice'] is True
    assert settings['random_first_alpha'] is True


@pytest.mark.unit
def test_only_the_host_may_change_the_rules(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)

    _configure(sock, code, uuids[2], free_trump_choice=True)

    assert 'Only the host' in _errors(sock)[0]
    assert _view(http, code, uuids[0])['settings']['free_trump_choice'] is False


@pytest.mark.unit
def test_the_rules_stop_moving_once_the_cards_are_dealt(clients):
    """Changing how a hand scores after players have seen their cards would
    move the goalposts under decisions they have already made."""
    http, sock = clients
    code, uuids = _lobby(http, sock)
    _start(sock, code, uuids[0])
    sock.get_received()

    _configure(sock, code, uuids[0], free_trump_choice=True)

    assert 'only be changed in the lobby' in _errors(sock)[0]
    assert _view(http, code, uuids[0])['settings']['free_trump_choice'] is False


@pytest.mark.unit
def test_a_setting_nobody_has_heard_of_is_refused_rather_than_stored(clients):
    """Stored silently, it would look configured and do nothing all game."""
    http, sock = clients
    code, uuids = _lobby(http, sock)

    _configure(sock, code, uuids[0], no_such_rule=True)

    assert 'Unknown setting' in _errors(sock)[0]
    assert 'no_such_rule' not in _view(http, code, uuids[0])['settings']


# --- 1: may a called card be a trump? ---
# Off, the alpha may not call a trump. On, they may — which makes the friend
# far harder to find, because a trump is a card nobody spends early.

def _at_friend_calling(http, sock, code, uuids, **settings):
    """A started game with trump declared, waiting on the friend call."""
    _configure(sock, code, uuids[0], free_trump_choice=True, **settings)
    _start(sock, code, uuids[0])
    alpha = _view(http, code, uuids[0])['alpha_uuid']
    sock.emit('declare_trump', {'game_code': code, 'player_uuid': alpha,
                                'suit': 'HEART', 'rank': 'NINE'})
    sock.get_received()
    return alpha


def _call(sock, code, alpha, suit, rank):
    sock.emit('call_friends', {
        'game_code': code, 'player_uuid': alpha,
        'calling_cards': [{'suit': suit, 'rank': rank, 'order': 1}],
    })


@pytest.mark.unit
def test_by_default_a_called_card_may_not_be_a_trump(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)
    alpha = _at_friend_calling(http, sock, code, uuids)

    _call(sock, code, alpha, 'HEART', 'ACE')

    assert 'must not be trumps' in _errors(sock)[0]


@pytest.mark.unit
def test_the_trump_rank_is_refused_in_any_suit_too(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)
    alpha = _at_friend_calling(http, sock, code, uuids)

    _call(sock, code, alpha, 'SPADE', 'NINE')

    assert 'must not be trumps' in _errors(sock)[0]


@pytest.mark.unit
def test_the_table_can_agree_to_allow_it(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)
    alpha = _at_friend_calling(http, sock, code, uuids, trumps_can_be_called=True)

    _call(sock, code, alpha, 'HEART', 'ACE')

    assert _errors(sock) == []
    assert _view(http, code, alpha)['game_event_state'] == 'waiting-on-alpha-kitty-sort'


# --- 2: what the alpha may declare as trump ---
# Off, trump is your own level in a suit you hold. On, anything goes.

def _at_trump(http, sock, code, uuids, **settings):
    if settings:
        _configure(sock, code, uuids[0], **settings)
    _start(sock, code, uuids[0])
    alpha = _view(http, code, uuids[0])['alpha_uuid']
    sock.get_received()
    return alpha


@pytest.mark.unit
def test_by_default_trump_has_to_be_your_own_level(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)
    alpha = _at_trump(http, sock, code, uuids)

    # Everyone starts on twos, so an ace is not theirs to declare.
    sock.emit('declare_trump', {'game_code': code, 'player_uuid': alpha,
                                'suit': 'HEART', 'rank': 'ACE'})

    assert 'your own level' in _errors(sock)[0]


def _deal_alpha(code, alpha, cards):
    """Put a known hand in front of the alpha.

    Hands are dealt at random, so a test that reads whatever the alpha happens
    to hold passes or skips depending on the shuffle. These rules turn on
    exactly what is in that hand, so the hand is the thing to pin down.
    """
    import Main

    gs = Main.get_redis_cache(code)
    gs.players_and_hand[alpha] = [Card(rank=rank, suit=suit) for rank, suit in cards]
    Main.update_redis_cache(gs)


@pytest.mark.unit
def test_and_has_to_be_a_card_you_are_holding(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)
    alpha = _at_trump(http, sock, code, uuids)
    _deal_alpha(code, alpha, [(Rank.TWO, Suit.HEART), (Rank.ACE, Suit.SPADE)])
    sock.get_received()

    sock.emit('declare_trump', {'game_code': code, 'player_uuid': alpha,
                                'suit': 'CLUB', 'rank': 'TWO'})

    assert 'not holding' in _errors(sock)[0]


@pytest.mark.unit
def test_a_level_card_you_do_hold_is_accepted(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)
    alpha = _at_trump(http, sock, code, uuids)
    _deal_alpha(code, alpha, [(Rank.TWO, Suit.HEART), (Rank.ACE, Suit.SPADE)])
    sock.get_received()

    sock.emit('declare_trump', {'game_code': code, 'player_uuid': alpha,
                                'suit': 'HEART', 'rank': 'TWO'})

    assert _errors(sock) == []
    assert _view(http, code, alpha)['declare_trump']['suit'] == 'HEART'


@pytest.mark.unit
def test_an_alpha_holding_none_of_their_level_may_name_any_suit(clients):
    """Somebody has to name a trump. The rule is there to stop the alpha
    inventing one, not to leave the game with no way forward."""
    http, sock = clients
    code, uuids = _lobby(http, sock)
    alpha = _at_trump(http, sock, code, uuids)
    _deal_alpha(code, alpha, [(Rank.ACE, Suit.SPADE), (Rank.KING, Suit.CLUB)])
    sock.get_received()

    sock.emit('declare_trump', {'game_code': code, 'player_uuid': alpha,
                                'suit': 'DIAMOND', 'rank': 'TWO'})

    assert _errors(sock) == []
    assert _view(http, code, alpha)['declare_trump']['suit'] == 'DIAMOND'


@pytest.mark.unit
def test_the_table_can_agree_to_free_choice(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)
    alpha = _at_trump(http, sock, code, uuids, free_trump_choice=True)

    sock.emit('declare_trump', {'game_code': code, 'player_uuid': alpha,
                                'suit': 'SPADE', 'rank': 'ACE'})

    assert _errors(sock) == []
    assert _view(http, code, alpha)['declare_trump']['rank'] == 'ACE'


# --- 3: who is the first alpha ---

@pytest.mark.unit
def test_by_default_the_host_is_the_first_alpha(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)

    _start(sock, code, uuids[0])

    assert _view(http, code, uuids[0])['alpha_uuid'] == uuids[0]


@pytest.mark.unit
def test_the_draw_can_land_on_anyone_at_the_table(clients, monkeypatch):
    """Including the host — a draw that excluded them would not be a draw."""
    import Main

    for seat in range(5):
        http, sock = clients
        code, uuids = _lobby(http, sock)
        _configure(sock, code, uuids[0], random_first_alpha=True)
        # Stand in for the shuffle so every seat is exercised, rather than
        # whichever ones a handful of real draws happen to reach.
        monkeypatch.setattr(Main.random, 'choice', lambda order, i=seat: order[i])

        _start(sock, code, uuids[0])

        assert _view(http, code, uuids[0])['alpha_uuid'] == uuids[seat]


@pytest.mark.unit
def test_a_drawn_alpha_is_announced_so_the_table_knows_why(clients, monkeypatch):
    import Main

    http, sock = clients
    code, uuids = _lobby(http, sock)
    _configure(sock, code, uuids[0], random_first_alpha=True)
    monkeypatch.setattr(Main.random, 'choice', lambda order: order[3])

    _start(sock, code, uuids[0])

    messages = [event['message'] for event in _view(http, code, uuids[0])['events']]
    assert any('drawn as the first alpha' in message for message in messages)


@pytest.mark.unit
def test_the_host_being_drawn_is_not_announced_as_a_draw(clients, monkeypatch):
    """Nothing happened that the table would not otherwise expect."""
    import Main

    http, sock = clients
    code, uuids = _lobby(http, sock)
    _configure(sock, code, uuids[0], random_first_alpha=True)
    monkeypatch.setattr(Main.random, 'choice', lambda order: order[0])

    _start(sock, code, uuids[0])

    messages = [event['message'] for event in _view(http, code, uuids[0])['events']]
    assert not any('drawn as the first alpha' in message for message in messages)


# --- each friend needs a card of their own ---
# Two rules naming the same card is one card doing both jobs: the first play to
# match satisfies both at once, so the second friend can never be found and the
# round never reaches all_friends_found.

def _call_many(sock, code, alpha, cards):
    sock.emit('call_friends', {
        'game_code': code, 'player_uuid': alpha,
        'calling_cards': [{'suit': suit, 'rank': rank, 'order': order}
                          for suit, rank, order in cards],
    })


def _at_friend_calling_for(http, sock, code, uuids, players):
    """Friend calling in a game big enough to need `players` friend cards."""
    _configure(sock, code, uuids[0], free_trump_choice=True)
    _start(sock, code, uuids[0])
    alpha = _view(http, code, uuids[0])['alpha_uuid']
    sock.emit('declare_trump', {'game_code': code, 'player_uuid': alpha,
                                'suit': 'HEART', 'rank': 'NINE'})
    sock.get_received()
    return alpha


def _lobby_of(http, sock, size):
    code = http.get("/create").get_json()['game_code']
    names = ('Ann', 'Bob', 'Cal', 'Dee', 'Eve', 'Fay', 'Gus')[:size]
    uuids = [
        http.get(f"/join/{code}?nick_name={name}").get_json()['new_player_uuid']
        for name in names
    ]
    sock.emit('join', {'game_code': code, 'player_uuid': uuids[0]})
    sock.get_received()
    return code, uuids


@pytest.mark.unit
def test_the_same_card_cannot_be_called_twice(clients):
    http, sock = clients
    code, uuids = _lobby_of(http, sock, 6)
    alpha = _at_friend_calling_for(http, sock, code, uuids, 2)

    _call_many(sock, code, alpha, [('SPADE', 'ACE', 1), ('SPADE', 'ACE', 1)])

    assert 'twice' in _errors(sock)[0]
    assert _view(http, code, alpha)['friend_calling_cards'] == []


@pytest.mark.unit
def test_two_copies_of_one_card_are_two_different_cards(clients):
    """What the order is for: the 1st and the 2nd Ace of Spades are two
    separate cards and can find two separate friends."""
    http, sock = clients
    code, uuids = _lobby_of(http, sock, 6)
    alpha = _at_friend_calling_for(http, sock, code, uuids, 2)

    _call_many(sock, code, alpha, [('SPADE', 'ACE', 1), ('SPADE', 'ACE', 2)])

    assert _errors(sock) == []
    assert len(_view(http, code, alpha)['friend_calling_cards']) == 2


@pytest.mark.unit
def test_the_same_order_of_two_different_cards_is_fine(clients):
    """Order counts copies of one card, so a 1st Ace and a 1st King do not
    collide."""
    http, sock = clients
    code, uuids = _lobby_of(http, sock, 6)
    alpha = _at_friend_calling_for(http, sock, code, uuids, 2)

    _call_many(sock, code, alpha, [('SPADE', 'ACE', 1), ('CLUB', 'KING', 1)])

    assert _errors(sock) == []
    assert len(_view(http, code, alpha)['friend_calling_cards']) == 2


@pytest.mark.unit
def test_the_refusal_names_the_card_that_was_repeated(clients):
    http, sock = clients
    code, uuids = _lobby_of(http, sock, 6)
    alpha = _at_friend_calling_for(http, sock, code, uuids, 2)

    _call_many(sock, code, alpha, [('SPADE', 'KING', 2), ('SPADE', 'KING', 2)])

    assert '2nd' in _errors(sock)[0]
