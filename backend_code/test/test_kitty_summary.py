"""The kitty on the round summary: what each card is worth, and where its points
went — doubled to the attackers when one of them took the last trick, to nobody
when the alpha team did, and uncounted when the host ended the round as a draw.
"""
import pytest

from Database import database
from Game.Components.Card import Card
from Game.Components.GameState import GameState
from Game.Modules.CardConstants import Rank, Suit
from Game.Modules.EventEnum import GameEventState
from Game.Systems.GameStateSystem import add_player, generate_player, set_player_as_alpha
from Game.Systems.SeatSystem import end_round_as_draw
from Game.Views.PlayerView import player_view_state


KITTY = [Card(suit=Suit.SPADE, rank=Rank.KING), Card(suit=Suit.CLUB, rank=Rank.THREE),
         Card(suit=Suit.HEART, rank=Rank.FIVE)]


@pytest.fixture
def main(tmp_path, monkeypatch):
    import Main

    db_file = str(tmp_path / "test_game_state.db")
    monkeypatch.setattr(database, "get_database", lambda: db_file)
    database.build_game_state_table()
    return Main


def _last_trick_taken_by(taker):
    """Five seats: seat 0 is alpha, seat 1 their revealed friend, the rest
    attacked. `taker` took the last trick."""
    gs = GameState()
    for i in range(5):
        add_player(gs, generate_player(name=f'p{i}'))
    seats = [str(player.uuid) for player in gs.player_order]
    set_player_as_alpha(gs, seats[0])
    gs.current_friends_of_alpha = [seats[1]]
    gs.card_out_of_play = list(KITTY)
    gs.last_trick_winner = seats[taker]
    return gs, seats


def _view(gs, seats):
    return player_view_state(gs, seats[0], now=0)


@pytest.mark.unit
def test_each_kitty_card_carries_its_points(main):
    gs, seats = _last_trick_taken_by(2)
    main.handle_end_of_round(gs)

    view = _view(gs, seats)
    assert view.kitty_card_points == [10, 0, 5]
    assert view.kitty_points == 15


@pytest.mark.unit
def test_an_attacker_taking_the_last_trick_takes_the_kitty_doubled(main):
    gs, seats = _last_trick_taken_by(2)
    main.handle_end_of_round(gs)

    view = _view(gs, seats)
    assert view.kitty_counted is True
    assert view.kitty_points_awarded == 30
    assert view.last_trick_winner_uuid == seats[2]
    assert view.round_attacker_points == 30


@pytest.mark.unit
def test_the_alpha_team_taking_the_last_trick_leaves_the_kitty_to_nobody(main):
    gs, seats = _last_trick_taken_by(1)
    main.handle_end_of_round(gs)

    view = _view(gs, seats)
    assert view.kitty_counted is True
    assert view.kitty_points_awarded == 0
    assert view.last_trick_winner_uuid == seats[1]


@pytest.mark.unit
def test_a_round_the_host_drew_leaves_the_kitty_uncounted():
    gs, seats = _last_trick_taken_by(2)
    end_round_as_draw(gs)

    view = _view(gs, seats)
    assert view.kitty_counted is False
    assert view.kitty_points_awarded == 0
    assert view.kitty_points == 15


@pytest.mark.unit
def test_nothing_about_the_kitty_is_sent_while_the_round_is_played():
    gs, seats = _last_trick_taken_by(2)
    gs.game_event_state = GameEventState.ROUND_STARTED

    view = _view(gs, seats)
    assert view.kitty_cards == []
    assert view.kitty_card_points == []
    assert view.kitty_points == 0
