/* HR-10: a finished trick stays face-up until its winner clears it.
 *
 * One copy, because three parts of the screen ask the same question and have to
 * agree on the answer: whether a countdown needs ticking at all, what the turn
 * indicator says while the table waits, and whether to draw the Clear button.
 *
 * Returns null when no trick is waiting — which is most of the time, and reads
 * at every call site as "nothing to say".
 */
export const trickClear = (view, serverNow) => {
    const since = view.trick_complete_since || 0;
    if (!since) return null;

    /* The winner is `winning_player_of_round`, not `current_player`. The server
     * leaves the turn where the last play left it until the trick is cleared,
     * so current_player is whoever played last — nearly always the wrong name
     * to put on screen here. */
    const winner = view.winning_player_of_round || null;
    return {
        winner,
        name: (winner && winner.name) || 'the winner',
        mine: Boolean(winner && view.uuid && winner.uuid === view.uuid),
        secondsLeft: since + (view.trick_clear_seconds || 0) - serverNow,
    };
};
