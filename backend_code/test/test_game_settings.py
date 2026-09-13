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
from Game.Modules.EventEnum import GameEventState


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
        hide_scores_until_round_end=False,
        scaled_level_promotion=False,
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


# --- 4: are the running point totals on the table? ---
# Off, everyone watches the score climb. On, nobody sees a total until the
# round is over. This is the one setting that takes something away rather than
# permitting something, and the only one enforced in the view rather than in a
# handler — so what these check is what leaves the server, not what is drawn.

def _mid_round(code, scores, all_friends_found=True):
    """A round in progress with known points already taken.

    Set on the stored state rather than played out: reaching a scoring trick
    through the socket takes a trump declaration, a friend call, a kitty
    discard and a deal that happens to hold the right cards, none of which this
    rule looks at. It reads the phase and the totals, so those are what is
    pinned. `all_friends_found` picks which of the two score displays the round
    would be showing, because the rule has to cover both.
    """
    import Main

    gs = Main.get_redis_cache(code)
    gs.game_event_state = GameEventState.ROUND_STARTED
    gs.players_round_score = dict(scores)
    gs.all_friends_found = all_friends_found
    Main.update_redis_cache(gs)


def _end_the_round(code):
    import Main

    gs = Main.get_redis_cache(code)
    gs.game_event_state = GameEventState.ROUND_ENDED
    Main.update_redis_cache(gs)


@pytest.mark.unit
def test_by_default_the_running_totals_are_on_the_table(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)
    _start(sock, code, uuids[0])
    _mid_round(code, {uuids[1]: 45})

    view = _view(http, code, uuids[2])
    assert view['scores_hidden'] is False
    assert view['players_round_score'][uuids[1]] == 45


@pytest.mark.unit
def test_the_table_can_agree_to_play_them_blind(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)
    _configure(sock, code, uuids[0], hide_scores_until_round_end=True)
    _start(sock, code, uuids[0])
    _mid_round(code, {uuids[1]: 45})

    view = _view(http, code, uuids[2])
    assert view['scores_hidden'] is True
    assert view['players_round_score'] == {}


@pytest.mark.unit
def test_the_totals_are_withheld_rather_than_merely_unrendered(clients):
    """The point of the rule is that nobody can look them up. Left in the
    payload for the client to skip, anyone with a devtools console would be
    playing a different game to the rest of the table."""
    http, sock = clients
    code, uuids = _lobby(http, sock)
    _configure(sock, code, uuids[0], hide_scores_until_round_end=True)
    _start(sock, code, uuids[0])
    _mid_round(code, {uuids[0]: 60, uuids[1]: 45})

    view = _view(http, code, uuids[0])
    assert view['alpha_team_points'] == 0
    assert view['defender_team_points'] == 0
    assert view['my_team_points'] == 0
    assert view['players_round_score'] == {}
    assert view['players_overall_score'] == {}


@pytest.mark.unit
def test_hidden_from_the_host_and_the_alpha_too(clients):
    """Nobody is exempt — a host who could still see the count would be the
    only player at the table keeping score."""
    http, sock = clients
    code, uuids = _lobby(http, sock)
    _configure(sock, code, uuids[0], hide_scores_until_round_end=True)
    _start(sock, code, uuids[0])
    _mid_round(code, {uuids[1]: 45})

    host_view = _view(http, code, uuids[0])
    assert host_view['hosting'] is True
    assert host_view['is_alpha'] is True
    assert host_view['scores_hidden'] is True
    assert host_view['players_round_score'] == {}


@pytest.mark.unit
def test_the_per_player_scores_are_hidden_before_the_friends_are_out(clients):
    """While friends are hidden the display is per player rather than per team,
    and that is the one carrying the numbers — so it is the one to cut."""
    http, sock = clients
    code, uuids = _lobby(http, sock)
    _configure(sock, code, uuids[0], hide_scores_until_round_end=True)
    _start(sock, code, uuids[0])
    _mid_round(code, {uuids[1]: 45}, all_friends_found=False)

    view = _view(http, code, uuids[2])
    assert view['scores_hidden'] is True
    assert view['players_round_score'] == {}


@pytest.mark.unit
def test_the_count_arrives_when_the_round_ends(clients):
    """Hidden *until the round ends* — a rule that never paid out would just be
    a game with no score."""
    http, sock = clients
    code, uuids = _lobby(http, sock)
    _configure(sock, code, uuids[0], hide_scores_until_round_end=True)
    _start(sock, code, uuids[0])
    _mid_round(code, {uuids[1]: 45})
    _end_the_round(code)

    view = _view(http, code, uuids[2])
    assert view['scores_hidden'] is False
    assert view['players_round_score'][uuids[1]] == 45
    assert view['defender_team_points'] == 45


@pytest.mark.unit
def test_the_setting_is_visible_to_everyone_before_they_commit(clients):
    """Whether you can see the score is most of what a round feels like, so a
    player deciding whether to stay has to be told which game this is."""
    http, sock = clients
    code, uuids = _lobby(http, sock)

    _configure(sock, code, uuids[0], hide_scores_until_round_end=True)

    assert _view(http, code, uuids[4])['settings']['hide_scores_until_round_end'] is True


@pytest.mark.unit
def test_the_host_cannot_reveal_the_scores_mid_round(clients):
    """The lobby-only rule matters more here than anywhere else: a host who
    could flip this during a round would get a look at totals nobody else
    gets, and could flip it straight back."""
    http, sock = clients
    code, uuids = _lobby(http, sock)
    _configure(sock, code, uuids[0], hide_scores_until_round_end=True)
    _start(sock, code, uuids[0])
    _mid_round(code, {uuids[1]: 45})
    sock.get_received()

    _configure(sock, code, uuids[0], hide_scores_until_round_end=False)

    assert 'only be changed in the lobby' in _errors(sock)[0]
    assert _view(http, code, uuids[0])['scores_hidden'] is True


# --- who is on fire ---
# A blind table is told who is ahead, never by how much. That is the one thing
# about the score the rule lets through, so what it lets through is worth
# pinning: the leader, everyone level with them, and nobody at all when there
# is nothing to lead.

@pytest.mark.unit
def test_the_player_in_front_is_named(clients):
    http, sock = clients
    code, uuids = _lobby(http, sock)
    _configure(sock, code, uuids[0], hide_scores_until_round_end=True)
    _start(sock, code, uuids[0])
    _mid_round(code, {uuids[1]: 45, uuids[2]: 20})

    assert _view(http, code, uuids[3])['top_scorer_uuids'] == [uuids[1]]


@pytest.mark.unit
def test_being_in_front_does_not_give_away_the_number(clients):
    """The whole trade the rule offers: you learn who, never how much."""
    http, sock = clients
    code, uuids = _lobby(http, sock)
    _configure(sock, code, uuids[0], hide_scores_until_round_end=True)
    _start(sock, code, uuids[0])
    _mid_round(code, {uuids[1]: 45, uuids[2]: 20})

    view = _view(http, code, uuids[3])
    assert view['top_scorer_uuids'] == [uuids[1]]
    assert view['players_round_score'] == {}
    assert view['defender_team_points'] == 0


@pytest.mark.unit
def test_everyone_level_at_the_top_is_named(clients):
    """Two players tied are both in front. Picking one would be inventing a
    lead that the scores do not support."""
    http, sock = clients
    code, uuids = _lobby(http, sock)
    _configure(sock, code, uuids[0], hide_scores_until_round_end=True)
    _start(sock, code, uuids[0])
    _mid_round(code, {uuids[1]: 45, uuids[2]: 45, uuids[3]: 10})

    assert sorted(_view(http, code, uuids[0])['top_scorer_uuids']) == sorted([uuids[1], uuids[2]])


@pytest.mark.unit
def test_nobody_is_in_front_of_a_scoreless_table(clients):
    """Every player starts the round on nothing. Five names alight because
    they are all tied on zero is not a leaderboard."""
    http, sock = clients
    code, uuids = _lobby(http, sock)
    _configure(sock, code, uuids[0], hide_scores_until_round_end=True)
    _start(sock, code, uuids[0])
    _mid_round(code, {uuid: 0 for uuid in uuids})

    assert _view(http, code, uuids[0])['top_scorer_uuids'] == []


@pytest.mark.unit
def test_nobody_is_in_front_once_the_round_is_over(clients):
    """The summary reports in full, so there is nothing left for a flame to
    say and the fire goes out with the round."""
    http, sock = clients
    code, uuids = _lobby(http, sock)
    _configure(sock, code, uuids[0], hide_scores_until_round_end=True)
    _start(sock, code, uuids[0])
    _mid_round(code, {uuids[1]: 45})
    _end_the_round(code)

    assert _view(http, code, uuids[0])['top_scorer_uuids'] == []
