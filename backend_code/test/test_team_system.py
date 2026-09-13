from Game.Components.GameState import GameState, DeclareCallingCard
from Game.Components.Card import Card
from Game.Modules.CardConstants import Suit, Rank
from Game.Systems.GameStateSystem import add_player, generate_player, set_player_as_alpha
from Game.Systems.TeamSystem import check_friend_card_played, friend_reveal_announcement
from Game.Systems.PointSystem import alpha_team_uuids, defender_team_uuids, team_round_points


def build_game(calling_cards, num_players=5):
    gs = GameState()
    for i in range(num_players):
        add_player(gs, generate_player(name=f'player{i}'))
    set_player_as_alpha(gs, gs.player_order[0].uuid)
    gs.friend_calling_cards = calling_cards
    return gs


def ace_of_clubs():
    return Card(suit=Suit.CLUB, rank=Rank.ACE)


def play(gs, player_uuid, cards):
    """Mirror handle_play_cards: cards land in the active pile before the check."""
    gs.cards_in_active_pile.extend(cards)
    check_friend_card_played(gs, player_uuid, cards)


def first_ace():
    return [DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=1)]


def second_ace():
    return [DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=2)]


class TestFriendDetection:
    def test_called_card_played_alone(self):
        gs = build_game(first_ace())
        bob = gs.player_order[1].uuid

        play(gs, bob, [ace_of_clubs()])

        assert gs.current_friends_of_alpha == [bob]

    def test_called_card_played_as_part_of_a_pair(self):
        """The first Ace arrives alongside the second — the player is still the friend."""
        gs = build_game(first_ace())
        bob = gs.player_order[1].uuid

        play(gs, bob, [ace_of_clubs(), ace_of_clubs()])

        assert gs.current_friends_of_alpha == [bob]

    def test_second_copy_called_and_pair_completes_it(self):
        gs = build_game(second_ace())
        bob = gs.player_order[1].uuid
        carol = gs.player_order[2].uuid

        play(gs, bob, [ace_of_clubs()])
        play(gs, carol, [ace_of_clubs(), ace_of_clubs()])

        assert gs.current_friends_of_alpha == [carol]

    def test_ordinal_is_respected_across_separate_plays(self):
        gs = build_game(second_ace())
        bob = gs.player_order[1].uuid
        carol = gs.player_order[2].uuid

        play(gs, bob, [ace_of_clubs()])
        assert gs.current_friends_of_alpha == []

        play(gs, carol, [ace_of_clubs()])
        assert gs.current_friends_of_alpha == [carol]

    def test_copies_in_earlier_tricks_still_count(self):
        gs = build_game(second_ace())
        bob = gs.player_order[1].uuid
        # An Ace played in an earlier trick has moved to the discard pile.
        gs.card_in_discard_pile.append(ace_of_clubs())

        play(gs, bob, [ace_of_clubs()])

        assert gs.current_friends_of_alpha == [bob]

    def test_unrelated_cards_reveal_nobody(self):
        gs = build_game(first_ace())
        bob = gs.player_order[1].uuid

        play(gs, bob, [Card(suit=Suit.HEART, rank=Rank.KING)])

        assert gs.current_friends_of_alpha == []

    def test_a_player_is_only_registered_once(self):
        gs = build_game([
            DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=1),
            DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=2),
        ])
        bob = gs.player_order[1].uuid

        play(gs, bob, [ace_of_clubs(), ace_of_clubs()])

        assert gs.current_friends_of_alpha == [bob]

    def test_alpha_playing_their_own_called_card_shrinks_the_team(self):
        gs = build_game(first_ace())
        alpha = gs.player_order[0].uuid

        play(gs, alpha, [ace_of_clubs()])

        assert alpha_team_uuids(gs) == {alpha}


class TestTeamScores:
    def test_teammates_share_one_total(self):
        gs = build_game(first_ace())
        alpha, bob, carol = (gs.player_order[i].uuid for i in range(3))
        gs.current_friends_of_alpha = [bob]
        gs.players_round_score[alpha] = 30
        gs.players_round_score[bob] = 20
        gs.players_round_score[carol] = 45

        alpha_points, defender_points = team_round_points(gs)

        assert alpha_points == 50
        assert defender_points == 45

    def test_unrevealed_friends_count_as_defenders_until_they_play(self):
        gs = build_game(first_ace())
        alpha, bob = gs.player_order[0].uuid, gs.player_order[1].uuid
        gs.players_round_score[alpha] = 10
        gs.players_round_score[bob] = 40

        assert team_round_points(gs) == (10, 40)

        play(gs, bob, [ace_of_clubs()])

        assert team_round_points(gs) == (50, 0)

    def test_teams_partition_every_player(self):
        gs = build_game(first_ace())
        gs.current_friends_of_alpha = [gs.player_order[1].uuid]

        everyone = {player.uuid for player in gs.player_order}

        assert alpha_team_uuids(gs) | defender_team_uuids(gs) == everyone
        assert alpha_team_uuids(gs) & defender_team_uuids(gs) == set()


# --- what check_friend_card_played reports back ---
# The play handler announces reveals from this return value, so it has to name
# each player exactly once, on the play that outed them.

def _reveal(gs, player_uuid, cards):
    """As `play`, but hands back who the play revealed."""
    gs.cards_in_active_pile.extend(cards)
    return check_friend_card_played(gs, player_uuid, cards)


def test_playing_the_called_card_reports_the_player():
    gs = build_game(first_ace())
    friend = gs.player_order[1].uuid

    assert _reveal(gs, friend, [ace_of_clubs()]) == [friend]


def test_an_ordinary_play_reveals_nobody():
    gs = build_game(first_ace())
    player = gs.player_order[1].uuid

    assert _reveal(gs, player, [Card(suit=Suit.HEART, rank=Rank.FIVE)]) == []


def test_a_friend_playing_on_without_a_called_card_is_not_reported_again():
    """Otherwise the same reveal is announced again every time they play."""
    gs = build_game(first_ace())
    friend = gs.player_order[1].uuid

    first = _reveal(gs, friend, [ace_of_clubs()])
    later = _reveal(gs, friend, [ace_of_clubs()])

    assert first == [friend]
    assert later == []
    assert gs.current_friends_of_alpha == [friend]


def test_a_second_called_card_reports_the_friend_again():
    """A double jump is news: the same player just filled another friend spot."""
    gs = build_game([
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=1),
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=2),
    ])
    friend = gs.player_order[1].uuid

    first = _reveal(gs, friend, [ace_of_clubs()])
    second = _reveal(gs, friend, [ace_of_clubs()])

    assert first == [friend]
    assert second == [friend]
    assert gs.current_friends_of_alpha == [friend]


def test_a_pair_covering_two_calls_is_reported_once():
    gs = build_game([
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=1),
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=2),
    ])
    friend = gs.player_order[1].uuid

    assert _reveal(gs, friend, [ace_of_clubs(), ace_of_clubs()]) == [friend]


def test_the_alpha_playing_their_own_called_card_is_reported():
    gs = build_game(first_ace())
    alpha = gs.player_order[0].uuid

    assert _reveal(gs, alpha, [ace_of_clubs()]) == [alpha]


# --- how a reveal is announced ---
# Worded by how many places on the alpha team the player now fills, so the
# unusual ones — a double jump, the alpha calling themselves — read as such.

def _announce(gs, player_uuid, cards, name='Bob'):
    revealed = _reveal(gs, player_uuid, cards)
    assert revealed == [player_uuid]
    return friend_reveal_announcement(gs, player_uuid, name)


def _three_calls():
    return [
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=1),
        DeclareCallingCard(suit=Suit.HEART, rank=Rank.KING, order=1),
        DeclareCallingCard(suit=Suit.SPADE, rank=Rank.QUEEN, order=1),
    ]


def test_an_ordinary_friend_joins():
    gs = build_game(first_ace())

    message, clause = _announce(gs, gs.player_order[1].uuid, [ace_of_clubs()])

    assert message == 'Bob has joined the alpha team'
    assert clause == 'joined the alpha team'


def test_a_friend_on_their_second_call_double_jumps():
    gs = build_game(_three_calls(), num_players=8)
    bob = gs.player_order[1].uuid
    _reveal(gs, bob, [ace_of_clubs()])

    message, clause = _announce(gs, bob, [Card(suit=Suit.HEART, rank=Rank.KING)])

    assert message == 'Bob has double jumped onto the alpha team, filling two friend spots'
    assert clause == 'double jumped onto the alpha team'


def test_a_pair_covering_two_calls_double_jumps_in_one_go():
    gs = build_game([
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=1),
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=2),
    ], num_players=6)

    _, clause = _announce(gs, gs.player_order[1].uuid, [ace_of_clubs(), ace_of_clubs()])

    assert clause == 'double jumped onto the alpha team'


def test_a_friend_on_their_third_call_triple_jumps():
    gs = build_game(_three_calls(), num_players=8)
    bob = gs.player_order[1].uuid
    _reveal(gs, bob, [ace_of_clubs()])
    _reveal(gs, bob, [Card(suit=Suit.HEART, rank=Rank.KING)])

    message, clause = _announce(gs, bob, [Card(suit=Suit.SPADE, rank=Rank.QUEEN)])

    assert message == 'Bob has triple jumped onto the alpha team, filling three friend spots'
    assert clause == 'triple jumped onto the alpha team'


def test_the_alpha_on_their_own_call_double_joins():
    gs = build_game(first_ace())
    alpha = gs.player_order[0].uuid

    message, clause = _announce(gs, alpha, [ace_of_clubs()], name='Ann')

    assert message == 'Ann has double joined the alpha team by playing a card they called themselves'
    assert clause == 'double joined the alpha team'


def test_the_alpha_on_a_second_own_call_triple_joins():
    gs = build_game(_three_calls(), num_players=8)
    alpha = gs.player_order[0].uuid
    _reveal(gs, alpha, [ace_of_clubs()])

    _, clause = _announce(gs, alpha, [Card(suit=Suit.HEART, rank=Rank.KING)], name='Ann')

    assert clause == 'triple joined the alpha team'


def test_another_friend_joining_does_not_change_how_the_first_is_counted():
    gs = build_game(_three_calls(), num_players=8)
    bob, carol = gs.player_order[1].uuid, gs.player_order[2].uuid
    _reveal(gs, bob, [ace_of_clubs()])

    _, clause = _announce(gs, carol, [Card(suit=Suit.HEART, rank=Rank.KING)], name='Carol')

    assert clause == 'joined the alpha team'


def test_the_reported_player_is_the_one_who_played_it():
    gs = build_game(first_ace())
    other = gs.player_order[2].uuid

    revealed = _reveal(gs, other, [ace_of_clubs()])

    assert revealed == [other]
    assert gs.current_friends_of_alpha == [other]


# --- which rule outed whom ---
# The called-cards strip shows the reveal against the rule that caused it, so
# each calling card has to carry its own trigger.

def test_the_rule_records_who_satisfied_it():
    gs = build_game(first_ace())
    friend = gs.player_order[1].uuid

    play(gs, friend, [ace_of_clubs()])

    assert gs.friend_calling_cards[0].revealed_by == friend


def test_an_untriggered_rule_names_nobody():
    gs = build_game([
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=1),
        DeclareCallingCard(suit=Suit.HEART, rank=Rank.KING, order=1),
    ])
    friend = gs.player_order[1].uuid

    play(gs, friend, [ace_of_clubs()])

    assert gs.friend_calling_cards[0].revealed_by == friend
    assert gs.friend_calling_cards[1].revealed_by == ''


def test_two_rules_are_credited_to_the_players_who_tripped_them():
    gs = build_game([
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=1),
        DeclareCallingCard(suit=Suit.HEART, rank=Rank.KING, order=1),
    ])
    first = gs.player_order[1].uuid
    second = gs.player_order[2].uuid

    play(gs, first, [ace_of_clubs()])
    play(gs, second, [Card(suit=Suit.HEART, rank=Rank.KING)])

    assert gs.friend_calling_cards[0].revealed_by == first
    assert gs.friend_calling_cards[1].revealed_by == second


def test_one_play_can_satisfy_two_rules_at_once():
    """A pair covers the 1st and 2nd copy, so both rules point at that player
    even though they only join the friends list once."""
    gs = build_game([
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=1),
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=2),
    ])
    friend = gs.player_order[1].uuid

    play(gs, friend, [ace_of_clubs(), ace_of_clubs()])

    assert [cc.revealed_by for cc in gs.friend_calling_cards] == [friend, friend]
    assert gs.current_friends_of_alpha == [friend]


def test_a_rule_keeps_the_player_who_got_there_first():
    gs = build_game([
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=1),
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=2),
    ])
    first = gs.player_order[1].uuid
    second = gs.player_order[2].uuid

    play(gs, first, [ace_of_clubs()])
    play(gs, second, [ace_of_clubs()])

    assert gs.friend_calling_cards[0].revealed_by == first
    assert gs.friend_calling_cards[1].revealed_by == second


def test_the_attribution_reaches_the_player_view():
    from Game.Views.PlayerView import player_view_state

    gs = build_game(first_ace())
    gs.game_code = 'test-game'
    friend = gs.player_order[1].uuid
    play(gs, friend, [ace_of_clubs()])

    view = player_view_state(gs, str(gs.player_order[0].uuid))

    assert view.friend_calling_cards[0].revealed_by == friend


def test_the_buried_kitty_is_shown_only_once_the_round_is_over():
    """Named mid-round it would hand the defenders the round; at the end it is
    part of the result."""
    from Game.Components.Card import Card
    from Game.Modules.CardConstants import Rank, Suit
    from Game.Modules.EventEnum import GameEventState
    from Game.Views.PlayerView import player_view_state

    gs = build_game(first_ace())
    gs.card_out_of_play = [Card(rank=Rank.KING, suit=Suit.SPADE)]
    defender = str(gs.player_order[2].uuid)

    gs.game_event_state = GameEventState.ROUND_STARTED
    assert player_view_state(gs, defender).kitty_cards == []

    gs.game_event_state = GameEventState.ROUND_ENDED
    assert player_view_state(gs, defender).kitty_cards == gs.card_out_of_play


def test_calling_cards_saved_before_this_still_load():
    """Old rows have calling cards with no revealed_by field."""
    from Game.Components.GameState import GameState as GS

    gs = build_game(first_ace())
    old_shape = gs.model_dump(mode='json')
    del old_shape['friend_calling_cards'][0]['revealed_by']

    reloaded = GS(**old_shape)

    assert reloaded.friend_calling_cards[0].revealed_by == ''


# --- every revealed friend is named against a rule ---
# The UI shows a reveal in one place: beside the called card that caused it.
# There is no separate list of friends, so a player who reaches the friends
# list without any rule naming them would simply not appear anywhere.

def _unattributed(gs):
    """Revealed friends that no calling card credits."""
    credited = {cc.revealed_by for cc in gs.friend_calling_cards if cc.revealed_by}
    return [uuid for uuid in gs.current_friends_of_alpha if uuid not in credited]


def test_a_revealed_friend_is_always_named_by_the_rule_that_revealed_them():
    gs = build_game(first_ace())
    friend = gs.player_order[1].uuid

    play(gs, friend, [ace_of_clubs()])

    assert gs.current_friends_of_alpha == [friend]
    assert _unattributed(gs) == []


def test_a_second_friend_on_a_later_copy_is_named_too():
    """Each copy of a called card is its own rule, so the second player to
    play one is credited against the second rule rather than falling through
    the first, which is already spoken for."""
    gs = build_game([
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=1),
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=2),
    ])
    first = gs.player_order[1].uuid
    second = gs.player_order[2].uuid

    play(gs, first, [ace_of_clubs()])
    play(gs, second, [ace_of_clubs()])

    assert gs.current_friends_of_alpha == [first, second]
    assert _unattributed(gs) == []


def test_a_copy_played_after_the_rules_are_used_up_reveals_nobody_new():
    """Counting runs across every pile, so a called position is consumed once
    and for all. Nothing can join the friends list without a rule left to
    name it."""
    gs = build_game(first_ace())
    first = gs.player_order[1].uuid
    late = gs.player_order[2].uuid

    play(gs, first, [ace_of_clubs()])
    # The trick ends and the pile moves to the discards, as it does in play.
    gs.card_in_discard_pile.extend(gs.cards_in_active_pile)
    gs.cards_in_active_pile.clear()
    play(gs, late, [ace_of_clubs()])

    assert gs.current_friends_of_alpha == [first]
    assert _unattributed(gs) == []


# --- when the sides are resolved ---
# all_friends_found is what tells the UI to show every side and switch to team
# totals. It has to come true once every called card is played, even when one
# player satisfied more than one of them.

def _two_calls():
    return [
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=1),
        DeclareCallingCard(suit=Suit.HEART, rank=Rank.KING, order=1),
    ]


def king_of_hearts():
    return Card(suit=Suit.HEART, rank=Rank.KING)


def test_sides_stay_open_while_a_called_card_is_unplayed():
    gs = build_game(_two_calls(), num_players=6)

    play(gs, gs.player_order[1].uuid, [ace_of_clubs()])

    assert gs.all_friends_found is False


def test_two_friends_on_two_cards_resolve_the_sides():
    gs = build_game(_two_calls(), num_players=6)

    play(gs, gs.player_order[1].uuid, [ace_of_clubs()])
    play(gs, gs.player_order[2].uuid, [king_of_hearts()])

    assert gs.all_friends_found is True


def test_a_double_jump_across_two_plays_resolves_the_sides():
    gs = build_game(_two_calls(), num_players=6)
    bob = gs.player_order[1].uuid

    play(gs, bob, [ace_of_clubs()])
    play(gs, bob, [king_of_hearts()])

    assert gs.current_friends_of_alpha == [bob]
    assert gs.all_friends_found is True


def test_a_double_jump_in_one_pair_resolves_the_sides():
    gs = build_game([
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=1),
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=2),
    ], num_players=6)

    play(gs, gs.player_order[1].uuid, [ace_of_clubs(), ace_of_clubs()])

    assert gs.all_friends_found is True


def test_the_alpha_calling_themselves_resolves_the_sides():
    gs = build_game(first_ace())
    alpha = gs.player_order[0].uuid

    play(gs, alpha, [ace_of_clubs()])

    assert alpha_team_uuids(gs) == {alpha}
    assert gs.all_friends_found is True


def test_the_alpha_playing_every_called_card_resolves_the_sides():
    gs = build_game(_two_calls(), num_players=6)
    alpha = gs.player_order[0].uuid

    play(gs, alpha, [ace_of_clubs()])
    play(gs, alpha, [king_of_hearts()])

    assert alpha_team_uuids(gs) == {alpha}
    assert gs.all_friends_found is True


def test_the_alpha_and_a_friend_sharing_the_calls_resolve_the_sides():
    gs = build_game(_two_calls(), num_players=6)
    alpha, bob = gs.player_order[0].uuid, gs.player_order[1].uuid

    play(gs, alpha, [ace_of_clubs()])
    assert gs.all_friends_found is False

    play(gs, bob, [king_of_hearts()])

    assert alpha_team_uuids(gs) == {alpha, bob}
    assert gs.all_friends_found is True


def test_a_pair_satisfying_two_rules_names_its_player_against_both():
    gs = build_game([
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=1),
        DeclareCallingCard(suit=Suit.CLUB, rank=Rank.ACE, order=2),
    ])
    friend = gs.player_order[1].uuid

    play(gs, friend, [ace_of_clubs(), ace_of_clubs()])

    assert gs.current_friends_of_alpha == [friend]
    assert _unattributed(gs) == []
