"""A play is laid on the table in order, not in the order its cards were picked.

Trumps first, then each suit, strongest to weakest — the order a hand is sorted
into — so identical cards sit together and a tractor reads 8 8 7 7.
"""
import pytest

from Database import database
from Game.Components.Card import Card
from Game.Modules.CardConstants import Rank, Suit
from Game.Systems.DecisionSystem import play_order
from test.seats import TableSockets, view
from test.test_trick_attribution_flow import _errors, _started_game


HEARTS_QUEENS = {'suit': Suit.HEART, 'rank': Rank.QUEEN}


def _cards(*pairs):
    return [Card(suit=suit, rank=rank) for rank, suit in pairs]


# --- the order itself ---

@pytest.mark.unit
def test_a_tractor_reads_high_to_low_with_its_pairs_together():
    picked = _cards((Rank.SEVEN, Suit.SPADE), (Rank.EIGHT, Suit.SPADE),
                    (Rank.SEVEN, Suit.SPADE), (Rank.EIGHT, Suit.SPADE))

    assert play_order(HEARTS_QUEENS, picked) == _cards(
        (Rank.EIGHT, Suit.SPADE), (Rank.EIGHT, Suit.SPADE),
        (Rank.SEVEN, Suit.SPADE), (Rank.SEVEN, Suit.SPADE))


@pytest.mark.unit
def test_trumps_come_first_strongest_first_then_each_suit():
    """Big joker, the trump card, the trump rank off-suit, the trump suit —
    then spades before clubs, as the hand sorts them."""
    picked = _cards((Rank.THREE, Suit.CLUB), (Rank.TWO, Suit.HEART),
                    (Rank.QUEEN, Suit.SPADE), (Rank.KING, Suit.SPADE),
                    (Rank.QUEEN, Suit.HEART), (Rank.JOKER, Suit.BIG))

    assert play_order(HEARTS_QUEENS, picked) == _cards(
        (Rank.JOKER, Suit.BIG), (Rank.QUEEN, Suit.HEART), (Rank.QUEEN, Suit.SPADE),
        (Rank.TWO, Suit.HEART), (Rank.KING, Suit.SPADE), (Rank.THREE, Suit.CLUB))


@pytest.mark.unit
def test_the_trump_rank_in_the_off_suits_sits_together_by_suit():
    picked = _cards((Rank.QUEEN, Suit.DIAMOND), (Rank.QUEEN, Suit.SPADE),
                    (Rank.QUEEN, Suit.CLUB), (Rank.QUEEN, Suit.SPADE))

    assert play_order(HEARTS_QUEENS, picked) == _cards(
        (Rank.QUEEN, Suit.SPADE), (Rank.QUEEN, Suit.SPADE),
        (Rank.QUEEN, Suit.CLUB), (Rank.QUEEN, Suit.DIAMOND))


@pytest.mark.unit
def test_the_same_cards_picked_in_any_order_come_out_the_same():
    picked = _cards((Rank.SEVEN, Suit.SPADE), (Rank.EIGHT, Suit.SPADE),
                    (Rank.EIGHT, Suit.SPADE), (Rank.SEVEN, Suit.SPADE))

    assert play_order(HEARTS_QUEENS, picked) == play_order(HEARTS_QUEENS, list(reversed(picked)))


# --- through the real handler ---

@pytest.fixture
def clients(tmp_path, monkeypatch):
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


@pytest.mark.unit
def test_a_tractor_picked_out_of_order_lands_on_the_trick_in_order(clients):
    """The fixture makes hearts and queens trump, so spade sevens and eights are
    a plain tractor. Picked 7 8 7 8; on the table, and as the lead to follow,
    8 8 7 7."""
    import Main

    http, sock = clients
    code, uuids = _started_game(http, sock)
    gs = Main.get_redis_cache(code)
    leader = gs.player_order[gs.current_player.index].uuid
    gs.players_and_hand[leader] = _cards(
        (Rank.SEVEN, Suit.SPADE), (Rank.EIGHT, Suit.SPADE),
        (Rank.SEVEN, Suit.SPADE), (Rank.EIGHT, Suit.SPADE),
    ) + gs.players_and_hand[leader][4:]
    Main.update_redis_cache(gs)

    sock.emit('play_cards', {
        'game_code': code, 'player_uuid': leader,
        'cards': [{'suit': 'SPADE', 'rank': rank} for rank in ('SEVEN', 'EIGHT', 'SEVEN', 'EIGHT')],
    })
    assert _errors(sock) == []

    seen = view(http, code, uuids[0])
    expected = [{'suit': 'SPADE', 'rank': rank} for rank in ('EIGHT', 'EIGHT', 'SEVEN', 'SEVEN')]
    assert [{'suit': c['suit'], 'rank': c['rank']} for c in seen['cards_in_active_pile']] == expected
    assert [{'suit': c['suit'], 'rank': c['rank']} for c in seen['leading_hand_of_subround']] == expected


# --- what the lead asks for, named for the trick area ---

@pytest.mark.unit
def test_the_view_names_what_the_lead_asks_for(clients):
    """Hearts and queens are trump in the fixture, so spades are a plain suit."""
    import Main

    http, sock = clients
    code, uuids = _started_game(http, sock)
    gs = Main.get_redis_cache(code)
    leader = gs.player_order[gs.current_player.index].uuid
    gs.players_and_hand[leader] = _cards(
        (Rank.EIGHT, Suit.SPADE), (Rank.EIGHT, Suit.SPADE)) + gs.players_and_hand[leader][2:]
    Main.update_redis_cache(gs)

    assert view(http, code, uuids[0])['lead_label'] == ''

    sock.emit('play_cards', {
        'game_code': code, 'player_uuid': leader,
        'cards': [{'suit': 'SPADE', 'rank': 'EIGHT'}] * 2,
    })
    assert _errors(sock) == []

    assert view(http, code, uuids[0])['lead_label'] == 'a pair in spades'


@pytest.mark.unit
def test_a_trump_lead_is_named_as_trumps(clients):
    import Main

    http, sock = clients
    code, uuids = _started_game(http, sock)
    gs = Main.get_redis_cache(code)
    leader = gs.player_order[gs.current_player.index].uuid
    gs.players_and_hand[leader] = _cards((Rank.QUEEN, Suit.CLUB)) + gs.players_and_hand[leader][1:]
    Main.update_redis_cache(gs)

    sock.emit('play_cards', {
        'game_code': code, 'player_uuid': leader,
        'cards': [{'suit': 'CLUB', 'rank': 'QUEEN'}],
    })
    assert _errors(sock) == []

    assert view(http, code, uuids[0])['lead_label'] == 'trumps'
