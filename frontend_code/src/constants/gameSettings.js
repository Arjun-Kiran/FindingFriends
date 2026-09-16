/* The house rules a host can change in the lobby.
 *
 * Names must match GameSettings in the backend's Game/Components/GameState.py —
 * the server refuses a key it does not know rather than storing it, so a typo
 * here surfaces as an error instead of a setting that quietly does nothing.
 *
 * Off is the game as HouseRules.md describes it, but two of them ship on:
 * random_first_alpha and hide_scores_until_round_end. The server sends the
 * values a table is actually playing with, so nothing here decides that.
 * Most are a permission
 * — on loosens one rule — but hide_scores_until_round_end takes something away
 * instead, so the wording of each label has to carry its own direction rather
 * than leaning on the list. The descriptions say what actually changes at the
 * table, not what the flag is called.
 */
export const GAME_SETTINGS = [
    {
        key: 'trumps_can_be_called',
        label: 'Trumps can be called as friend cards',
        description: 'The alpha may name a trump. Friends are much harder to find, '
            + 'because nobody spends a trump early.',
    },
    {
        key: 'free_trump_choice',
        label: 'Alpha may declare any trump',
        description: 'Any suit and any rank, ignoring their level and what they hold.',
    },
    {
        key: 'random_first_alpha',
        label: 'Draw the first alpha at random',
        description: 'Rather than the host taking it. Only the first — after that '
            + 'the seat passes by the usual rules.',
    },
    {
        key: 'hide_scores_until_round_end',
        label: 'Hide points until the round ends',
        description: 'Nobody sees a running total — keep count yourself from the '
            + 'cards played. The full scores arrive with the round summary.',
    },
    {
        key: 'scaled_level_promotion',
        label: 'Bigger wins climb more levels',
        description: 'The traditional scoring: the defenders\' points decide the '
            + 'result, a big margin is worth up to three levels, and some rounds '
            + 'are a draw. Off, the side with more points wins and climbs one level.',
    },
    /* A choice rather than a switch: Lobby draws a dropdown for any setting
     * with options. Values match AlphaDeclarationOrder in the backend. */
    {
        key: 'alpha_declaration_order',
        label: 'Order of the alpha\'s opening steps',
        description: 'What the alpha does, in turn, before the first trick.',
        defaultValue: 'trump-kitty-friends',
        options: [
            { value: 'trump-friends-kitty', label: 'Trump Suit → Call Friends → Kitty' },
            { value: 'trump-kitty-friends', label: 'Trump Suit → Kitty → Call Friends' },
            { value: 'kitty-trump-friends', label: 'Kitty → Trump Suit → Call Friends' },
        ],
    },
];
