/* The house rules a host can change in the lobby.
 *
 * Names must match GameSettings in the backend's Game/Components/GameState.py —
 * the server refuses a key it does not know rather than storing it, so a typo
 * here surfaces as an error instead of a setting that quietly does nothing.
 *
 * Each is a permission: off is the game as ZhaoPengyou_Rules.md describes it,
 * on loosens one rule. The descriptions say what actually changes at the table,
 * not what the flag is called.
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
];
