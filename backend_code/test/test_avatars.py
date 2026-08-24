import pytest
from faker import Faker

from Game.Components.GameState import GameState
from Game.Modules.Avatars import (
    ANIMAL_AVATARS, available_avatars, is_valid_avatar, pick_avatar,
)
from Game.Systems.GameStateSystem import (
    add_player, generate_player, set_player_avatar, taken_avatars,
)
from Game.Views.PlayerView import player_view_state


def _game_with(count: int) -> tuple:
    f = Faker()
    gs = GameState()
    gs.game_code = 'test-game'
    players = [generate_player(f.first_name()) for _ in range(count)]
    for player in players:
        add_player(gs, player)
    return gs, players


@pytest.mark.unit
def test_catalog_has_no_duplicates():
    assert len(ANIMAL_AVATARS) == len(set(ANIMAL_AVATARS))


@pytest.mark.unit
def test_is_valid_avatar_rejects_anything_not_offered():
    assert is_valid_avatar(ANIMAL_AVATARS[0])
    assert not is_valid_avatar('')
    assert not is_valid_avatar('not an emoji')
    # A real emoji that simply is not in the catalog.
    assert not is_valid_avatar('🍕')


@pytest.mark.unit
def test_available_avatars_excludes_taken():
    taken = ANIMAL_AVATARS[:3]
    free = available_avatars(taken)
    assert not set(free) & set(taken)
    assert len(free) == len(ANIMAL_AVATARS) - 3


@pytest.mark.unit
def test_pick_avatar_never_returns_a_taken_one():
    taken = ANIMAL_AVATARS[:-1]
    assert pick_avatar(taken) == ANIMAL_AVATARS[-1]


@pytest.mark.unit
def test_pick_avatar_falls_back_when_everything_is_taken():
    # A duplicate beats handing back nothing at all.
    assert pick_avatar(ANIMAL_AVATARS) in ANIMAL_AVATARS


@pytest.mark.unit
def test_joining_players_are_auto_assigned_unique_avatars():
    gs, players = _game_with(5)
    avatars = [p.avatar for p in gs.player_order]
    assert all(is_valid_avatar(a) for a in avatars)
    assert len(set(avatars)) == 5


@pytest.mark.unit
def test_a_chosen_avatar_survives_joining():
    gs = GameState()
    chosen = ANIMAL_AVATARS[4]
    add_player(gs, generate_player('Ann', avatar=chosen))
    assert gs.player_order[0].avatar == chosen


@pytest.mark.unit
def test_joining_with_a_taken_avatar_gets_a_different_one():
    gs = GameState()
    chosen = ANIMAL_AVATARS[4]
    add_player(gs, generate_player('Ann', avatar=chosen))
    add_player(gs, generate_player('Bob', avatar=chosen))
    assert gs.player_order[1].avatar != chosen
    assert is_valid_avatar(gs.player_order[1].avatar)


@pytest.mark.unit
def test_set_player_avatar_updates_the_player():
    gs, players = _game_with(2)
    target = available_avatars(taken_avatars(gs))[0]
    assert set_player_avatar(gs, str(players[0].uuid), target)
    assert gs.player_dict[str(players[0].uuid)].avatar == target


@pytest.mark.unit
def test_set_player_avatar_rejects_one_another_player_holds():
    gs, players = _game_with(2)
    assert not set_player_avatar(gs, str(players[0].uuid), players[1].avatar)


@pytest.mark.unit
def test_set_player_avatar_allows_reselecting_your_own():
    gs, players = _game_with(2)
    mine = players[0].avatar
    assert set_player_avatar(gs, str(players[0].uuid), mine)


@pytest.mark.unit
def test_set_player_avatar_rejects_junk():
    gs, players = _game_with(2)
    assert not set_player_avatar(gs, str(players[0].uuid), '<script>alert(1)</script>')
    assert not set_player_avatar(gs, str(players[0].uuid), '')


@pytest.mark.unit
def test_set_player_avatar_writes_through_after_a_save_reload_cycle():
    """player_order and player_dict stop sharing Player objects once the game
    state has been through the database, and every handler works on a reloaded
    state — so a write that touched only one of them would be invisible in
    player_list."""
    gs, players = _game_with(3)
    reloaded = GameState(**gs.model_dump(mode='json'))
    assert reloaded.player_dict[str(players[0].uuid)] is not reloaded.player_order[0]

    target = available_avatars(taken_avatars(reloaded))[0]
    assert set_player_avatar(reloaded, str(players[0].uuid), target)

    assert reloaded.player_dict[str(players[0].uuid)].avatar == target
    assert reloaded.player_order[0].avatar == target


@pytest.mark.unit
def test_player_view_carries_avatars():
    gs, players = _game_with(5)
    view = player_view_state(gs, str(players[0].uuid))

    assert view.avatar == players[0].avatar
    assert view.avatar_choices == ANIMAL_AVATARS
    # Everyone else's avatar rides along on player_list.
    assert all(p.avatar for p in view.player_list)


@pytest.mark.unit
def test_player_view_json_keeps_avatars_as_strings():
    gs, players = _game_with(5)
    payload = player_view_state(gs, str(players[0].uuid)).to_json_dict()

    assert payload['avatar'] == players[0].avatar
    assert payload['player_list'][0]['avatar'] == gs.player_order[0].avatar
