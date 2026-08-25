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
    FRIEND: '🤝',
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

/** The two sides. Alpha shares the crown with the alpha player on purpose. */
export const TEAM_EMOJI = {
    ALPHA: '👑',
    DEFENDER: '🛡️',
};

/** Fallback for a player whose avatar is missing — games saved before avatars
 *  existed still have players with none. */
export const DEFAULT_AVATAR = '🎲';
