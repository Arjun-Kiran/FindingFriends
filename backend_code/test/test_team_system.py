from Game.Components.GameState import GameState, DeclareCallingCard
from Game.Components.Card import Card
from Game.Modules.CardConstants import Suit, Rank
from Game.Systems.GameStateSystem import add_player, generate_player, set_player_as_alpha
from Game.Systems.TeamSystem import check_friend_card_played
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
