/* Emoji used as iconography across the UI.
 *
 * One place, so a concept never picks up two different glyphs in two
 * components — the crown means alpha everywhere or it means nothing.
 *
 * Every emoji here decorates a label rather than replacing one. On its own an
 * emoji is ambiguous to a reader and silent-or-verbose to a screen reader, so
 * the text stays and the glyph is marked aria-hidden. The exception is the
 * player avatar, which genuinely is the player's identity — that one gets a
 * label of its own.
 */

/** Who someone is at the table. */
export const ROLE_EMOJI = {
    ALPHA: '👑',
    HOST: '🎩',
    YOU: '🙋',
};

/** What is happening to someone right now. */
export const STATUS_EMOJI = {
    CURRENT_TURN: '👉',
    DISCONNECTED: '🔌',
    RECONNECTING: '🔄',
    ERROR: '❗',
};

/** Scores, levels and outcomes. */
export const RESULT_EMOJI = {
    WINNER: '🏆',
    PROMOTION: '⬆️',
    POINTS: '💎',
    DRAW: '⚖️',
    /* The play currently winning the trick. Not reused for anything else —
       a glyph that means two things means neither. */
    WINNING_TRICK: '⭐',
};

/* Marks drawn on a card in your own hand.
 *
 * Deliberately not a star: RESULT_EMOJI.WINNING_TRICK already means "this play
 * is winning", and a trump card in your hand is not that. */
export const CARD_EMOJI = {
    TRUMP: '✨',
};

/* The two sides, as an attacking/defending pair — the alpha team is trying to
 * take points off the table and the defenders are trying to hold them.
 *
 * Not the crown, even though the alpha player wears one: a side is not a
 * person. Sharing the glyph meant a crown in the scores bar read as "the alpha
 * player's points" rather than "the alpha team's points", which is a different
 * number once friends have revealed themselves. */
export const TEAM_EMOJI = {
    ALPHA: '⚔️',
    DEFENDER: '🛡️',
};

/** Fallback for a player whose avatar is missing — games saved before avatars
 *  existed still have players with none. */
export const DEFAULT_AVATAR = '🎲';
