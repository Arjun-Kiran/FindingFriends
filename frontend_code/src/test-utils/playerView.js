/* Fixtures mirroring the backend's PlayerView payload.
 *
 * Contract notes (see backend Game/Views/PlayerView.py):
 *   - card suit/rank arrive as enum NAMES ('HEART', 'ACE')
 *   - player levels arrive as enum VALUES (1..13, where ACE === 13)
 *   - game_event_state arrives as the enum's string value ('round-started')
 */

export const PLAYERS = [
    { uuid: 'uuid-alice', name: 'Alice' },
    { uuid: 'uuid-bob', name: 'Bob' },
    { uuid: 'uuid-carol', name: 'Carol' },
    { uuid: 'uuid-dave', name: 'Dave' },
    { uuid: 'uuid-erin', name: 'Erin' },
];

export const ME = PLAYERS[0];

export const card = (rank, suit) => ({ rank, suit });

/** A PlayerView with every field the frontend reads, defaulted to empty. */
export const playerView = (overrides = {}) => ({
    name: ME.name,
    uuid: ME.uuid,
    can_start_game: false,
    my_turn: false,
    hosting: false,
    is_alpha: false,
    on_alpha_team: false,
    number_of_players: PLAYERS.length,
    current_player: null,
    leading_player: null,
    winning_player_of_round: null,
    player_list: PLAYERS,
    disconnected_players: [],
    player_hand: [],
    players_round_score: {},
    players_overall_score: {},
    alpha_team_points: 0,
    defender_team_points: 0,
    my_team_points: 0,
    game_event_state: 'waiting-for-player-to-join',
    game_code: 'below-adopt-havoc',
    declare_trump: { rank: null, suit: null },
    cards_in_active_pile: [],
    leading_hand_of_subround: [],
    kitty_size: 0,
    my_level: 1,
    player_levels: PLAYERS.reduce((acc, p) => ({ ...acc, [p.uuid]: 1 }), {}),
    friend_calling_cards: [],
    num_friends_to_call: 0,
    revealed_friends: [],
    all_friends_found: false,
    round_winner_side: '',
    round_defender_points: 0,
    round_promotion_levels: 0,
    round_promoted_players: [],
    game_winner: '',
    events: [],
    ...overrides,
});

export const sessionInfo = (overrides = {}) => ({
    game_code: 'below-adopt-havoc',
    user_name: ME.name,
    user_uuid: ME.uuid,
    game_link: `/game/below-adopt-havoc/player/${ME.uuid}`,
    host: true,
    ...overrides,
});
