import { TEAM_EMOJI } from '../constants/emoji';

/* Which side a player may be SHOWN as, and how to draw it.
 *
 * One copy, deliberately. Sides are the game's central secret — a friend is
 * indistinguishable from a defender until they play a called card (see
 * alpha_team_uuids in the backend's PointSystem, which says so in as many
 * words) — and the server never sends per-player team membership because of
 * it. Every place that draws a side has to work it out here, or two of them
 * will drift apart and one will end up showing what the other is hiding.
 */

export const TEAM_MARK = {
    alpha: { emoji: TEAM_EMOJI.ALPHA, label: 'Alpha team' },
    defender: { emoji: TEAM_EMOJI.DEFENDER, label: 'Defenders' },
};

/** 'alpha', 'defender', or '' for "not known yet". */
export const teamOf = ({
    playerUuid,
    alphaUuid = '',
    revealedFriends = [],
    allFriendsFound = false,
}) => {
    // No alpha yet means no sides yet.
    if (!alphaUuid) return '';

    // The alpha, and anyone who has outed themselves by playing a called card.
    if (playerUuid === alphaUuid || revealedFriends.includes(playerUuid)) return 'alpha';

    /* Nobody is a defender until the last friend is out.
     *
     * Not even you. This used to answer "is it me?" with the view's
     * `on_alpha_team`, which sounds like it means "is a defender" and does not:
     * the server sets it from `alpha_team_uuids`, which is the alpha plus the
     * friends who have ALREADY REVEALED. A player still holding a called card
     * is not in it, so their own shield would sit there through the round and
     * then flip to swords the moment they played the card. Better to say
     * nothing than to say the wrong side. */
    return allFriendsFound ? 'defender' : '';
};
