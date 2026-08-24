"""The trick pile records who played each card.

The pile and its attribution are grown and cleared together, so these pin that
they never fall out of step — a mismatch would put the wrong player's avatar
under a card, which is worse than showing none.
"""
import pytest
from faker import Faker

from Game.Components.GameState import GameState
from Game.Modules.CardConstants import Rank, Suit
from Game.Components.Card import Card
from Game.Systems.GameStateSystem import (
    add_player, clear_active_pile, generate_player, play_cards_into_active_pile,
    reset_round, set_player_as_leading_player,
)
from Game.Views.PlayerView import player_view_state


def _game_with_players(count=5):
    f = Faker()
    gs = GameState()
    gs.game_code = 'test-game'
    players = [generate_player(f.first_name()) for _ in range(count)]
    for player in players:
        add_player(gs, player)
    return gs, players


def _card(rank, suit):
    return Card(rank=rank, suit=suit)


@pytest.mark.unit
def test_a_play_is_recorded_against_its_player():
    gs, players = _game_with_players()
    play_cards_into_active_pile(gs, str(players[1].uuid), [_card(Rank.ACE, Suit.HEART)])

    assert gs.active_pile_player_uuids == [str(players[1].uuid)]


@pytest.mark.unit
def test_a_multi_card_play_records_one_uuid_per_card():
    gs, players = _game_with_players()
    cards = [_card(Rank.ACE, Suit.HEART), _card(Rank.ACE, Suit.SPADE)]
    play_cards_into_active_pile(gs, str(players[1].uuid), cards)

    assert gs.active_pile_player_uuids == [str(players[1].uuid)] * 2


@pytest.mark.unit
def test_attribution_stays_the_same_length_as_the_pile():
    gs, players = _game_with_players()
    play_cards_into_active_pile(gs, str(players[0].uuid), [_card(Rank.TWO, Suit.CLUB)])
    play_cards_into_active_pile(gs, str(players[1].uuid), [
        _card(Rank.THREE, Suit.CLUB), _card(Rank.FOUR, Suit.CLUB),
    ])
    play_cards_into_active_pile(gs, str(players[2].uuid), [_card(Rank.FIVE, Suit.CLUB)])

    assert len(gs.active_pile_player_uuids) == len(gs.cards_in_active_pile) == 4


@pytest.mark.unit
def test_plays_keep_their_order():
    gs, players = _game_with_players()
    for player, rank in zip(players[:3], (Rank.TWO, Rank.THREE, Rank.FOUR)):
        play_cards_into_active_pile(gs, str(player.uuid), [_card(rank, Suit.CLUB)])

    assert gs.active_pile_player_uuids == [str(p.uuid) for p in players[:3]]
    assert [c.rank for c in gs.cards_in_active_pile] == [Rank.TWO, Rank.THREE, Rank.FOUR]


@pytest.mark.unit
def test_clearing_the_pile_clears_the_attribution():
    gs, players = _game_with_players()
    play_cards_into_active_pile(gs, str(players[0].uuid), [_card(Rank.TWO, Suit.CLUB)])

    clear_active_pile(gs)

    assert gs.cards_in_active_pile == []
    assert gs.active_pile_player_uuids == []


@pytest.mark.unit
def test_ending_a_trick_clears_the_attribution_too():
    """reset_round moves the pile to the discard heap; leaving the uuids behind
    would mislabel the next trick's first cards."""
    gs, players = _game_with_players()
    set_player_as_leading_player(gs, player_uuid=str(players[0].uuid))
    gs.winning_player_of_round.player_uuid = str(players[0].uuid)
    play_cards_into_active_pile(gs, str(players[0].uuid), [_card(Rank.TWO, Suit.CLUB)])

    reset_round(gs)

    assert gs.cards_in_active_pile == []
    assert gs.active_pile_player_uuids == []
    assert len(gs.card_in_discard_pile) == 1


@pytest.mark.unit
def test_the_view_carries_the_attribution():
    gs, players = _game_with_players()
    play_cards_into_active_pile(gs, str(players[3].uuid), [_card(Rank.ACE, Suit.SPADE)])

    view = player_view_state(gs, str(players[0].uuid))

    assert view.active_pile_player_uuids == [str(players[3].uuid)]
    assert len(view.active_pile_player_uuids) == len(view.cards_in_active_pile)


@pytest.mark.unit
def test_the_json_payload_carries_the_attribution():
    gs, players = _game_with_players()
    play_cards_into_active_pile(gs, str(players[3].uuid), [_card(Rank.ACE, Suit.SPADE)])

    payload = player_view_state(gs, str(players[0].uuid)).to_json_dict()

    assert payload['active_pile_player_uuids'] == [str(players[3].uuid)]


@pytest.mark.unit
def test_attribution_survives_a_save_reload_cycle():
    gs, players = _game_with_players()
    play_cards_into_active_pile(gs, str(players[2].uuid), [_card(Rank.KING, Suit.HEART)])

    reloaded = GameState(**gs.model_dump(mode='json'))

    assert reloaded.active_pile_player_uuids == [str(players[2].uuid)]


@pytest.mark.unit
def test_a_game_saved_before_attribution_existed_still_loads():
    """Old rows in the database have a pile but no uuids beside it."""
    gs, players = _game_with_players()
    play_cards_into_active_pile(gs, str(players[0].uuid), [_card(Rank.TWO, Suit.CLUB)])
    old_shape = gs.model_dump(mode='json')
    del old_shape['active_pile_player_uuids']

    reloaded = GameState(**old_shape)

    assert reloaded.active_pile_player_uuids == []
    assert len(reloaded.cards_in_active_pile) == 1
