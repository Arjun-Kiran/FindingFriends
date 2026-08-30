"""The hint telling a player which of their own cards they may still play.

The flags ride along on the player's view, so the two things that matter are
that they line up with the hand as SENT — which the view has already sorted —
and that they are only worked out when they mean something.
"""
import pytest
from faker import Faker

from Game.Components.Card import Card
from Game.Components.GameState import GameState, DeclareTrump
from Game.Modules.CardConstants import Rank, Suit
from Game.Modules.EventEnum import GameEventState
from Game.Systems.GameStateSystem import add_player, generate_player
from Game.Views.PlayerView import player_view_state


def _card(rank, suit):
    return Card(rank=rank, suit=suit)


def _table(hand, leading, *, my_turn=True,
           state=GameEventState.ROUND_STARTED):
    """A game where it is (or is not) my turn and `leading` has been led."""
    f = Faker()
    gs = GameState()
    gs.game_code = 'test-game'
    players = [generate_player(f.first_name()) for _ in range(5)]
    for player in players:
        add_player(gs, player)
    me = players[1]
    gs.game_event_state = state
    gs.declare_trump = DeclareTrump(rank=Rank.FIVE, suit=Suit.HEART)
    gs.players_and_hand[str(me.uuid)] = list(hand)
    gs.leading_hand_of_subround = list(leading)
    gs.current_player.player_uuid = str(me.uuid if my_turn else players[2].uuid)
    return gs, str(me.uuid)


def _hint(view):
    """The hint paired with the cards it describes, as the player sees them."""
    return [(card.rank, card.suit, playable)
            for card, playable in zip(view.player_hand, view.playable_hand_cards)]


@pytest.mark.unit
def test_the_flags_line_up_with_the_hand_as_it_is_sent():
    """The client decides how a hand is laid out, so the flags have to describe
    the hand in the order the server actually sends it — anything else rings
    whichever cards happen to land in those positions on screen."""
    hand = [_card(Rank.TWO, Suit.CLUB), _card(Rank.ACE, Suit.SPADE),
            _card(Rank.KING, Suit.SPADE)]
    gs, me = _table(hand, [_card(Rank.JACK, Suit.SPADE)])

    view = player_view_state(gs, me)

    assert _hint(view) == [
        (Rank.TWO, Suit.CLUB, False),
        (Rank.ACE, Suit.SPADE, True),
        (Rank.KING, Suit.SPADE, True),
    ]


@pytest.mark.unit
def test_the_hand_is_sent_in_the_order_the_engine_holds_it():
    """No server-side sort: laying out a hand is the client's job, and a sort
    here would fight the player's own arrangement on every push."""
    hand = [_card(Rank.KING, Suit.SPADE), _card(Rank.TWO, Suit.CLUB),
            _card(Rank.JOKER, Suit.BIG)]
    gs, me = _table(hand, [])

    sent = [(card.rank, card.suit) for card in player_view_state(gs, me).player_hand]

    assert sent == [(Rank.KING, Suit.SPADE), (Rank.TWO, Suit.CLUB), (Rank.JOKER, Suit.BIG)]


@pytest.mark.unit
def test_there_is_one_flag_for_every_card_in_the_hand():
    hand = [_card(Rank.TWO, Suit.CLUB), _card(Rank.ACE, Suit.SPADE)]
    gs, me = _table(hand, [_card(Rank.JACK, Suit.SPADE)])

    view = player_view_state(gs, me)

    assert len(view.playable_hand_cards) == len(view.player_hand)


@pytest.mark.unit
def test_leading_a_trick_leaves_every_card_available():
    hand = [_card(Rank.TWO, Suit.CLUB), _card(Rank.ACE, Suit.SPADE)]
    gs, me = _table(hand, [])

    assert player_view_state(gs, me).playable_hand_cards == [True, True]



@pytest.mark.unit
def test_the_hint_is_there_before_your_turn_comes_round():
    """A player watching a trick reach them wants to know what they will be
    able to answer with. It is their own hand against a lead the whole table
    can see, so waiting to say so buys nothing."""
    hand = [_card(Rank.TWO, Suit.CLUB), _card(Rank.ACE, Suit.SPADE)]
    gs, me = _table(hand, [_card(Rank.JACK, Suit.SPADE)], my_turn=False)

    assert player_view_state(gs, me).playable_hand_cards == [False, True]


@pytest.mark.unit
def test_it_says_the_same_thing_whoever_is_on_turn():
    hand = [_card(Rank.TWO, Suit.CLUB), _card(Rank.ACE, Suit.SPADE)]
    leading = [_card(Rank.JACK, Suit.SPADE)]

    on_turn, me = _table(hand, leading)
    waiting, also_me = _table(hand, leading, my_turn=False)

    assert (player_view_state(on_turn, me).playable_hand_cards
            == player_view_state(waiting, also_me).playable_hand_cards)


@pytest.mark.unit
def test_nothing_is_worked_out_outside_the_play_phase():
    """The kitty hand is not a hand being played into a trick, and it has cards
    in it that are not in players_and_hand at all."""
    hand = [_card(Rank.TWO, Suit.CLUB), _card(Rank.ACE, Suit.SPADE)]
    gs, me = _table(hand, [], state=GameEventState.WAITING_ON_ALPHA_KITTY_SORT)

    assert player_view_state(gs, me).playable_hand_cards == []


@pytest.mark.unit
def test_the_hint_survives_the_trip_to_the_frontend_as_plain_booleans():
    hand = [_card(Rank.TWO, Suit.CLUB), _card(Rank.ACE, Suit.SPADE)]
    gs, me = _table(hand, [_card(Rank.JACK, Suit.SPADE)])

    payload = player_view_state(gs, me).to_json_dict()

    assert payload['playable_hand_cards'] == [False, True]
