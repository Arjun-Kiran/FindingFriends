import { TEAM_EMOJI } from '../constants/emoji';

/* Which side a player may be SHOWN as, and how to draw it.
 *
 * One copy, deliberately. Sides are the game's central secret — a friend is
 * indistinguishable from an attacker until they play a called card (see
 * alpha_team_uuids in the backend's PointSystem, which says so in as many
 * words) — and the server never sends per-player team membership because of
 * it. Every place that draws a side has to work it out here, or two of them
 * will drift apart and one will end up showing what the other is hiding.
 */

export const TEAM_MARK = {
    alpha: { emoji: TEAM_EMOJI.ALPHA, label: 'Alpha team' },
    attacker: { emoji: TEAM_EMOJI.ATTACKER, label: 'Attackers' },
};

/** 'alpha', 'attacker', or '' for "not known yet". */
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

    /* Nobody is an attacker until the last friend is out.
     *
     * Not even you. This used to answer "is it me?" with the view's
     * `on_alpha_team`, which sounds like it means "is an attacker" and does not:
     * the server sets it from `alpha_team_uuids`, which is the alpha plus the
     * friends who have ALREADY REVEALED. A player still holding a called card
     * is not in it, so their own swords would sit there through the round and
     * then flip to the shield the moment they played the card. Better to say
     * nothing than to say the wrong side. */
    return allFriendsFound ? 'attacker' : '';
};

/** 'alpha' or 'attacker' as things stand right now, or '' before there is an alpha.
 *
 * Not for drawing a side — that is teamOf's job, and it refuses to guess. This
 * one guesses on purpose, for "is the trick going to the other side?": anyone
 * not yet on the alpha team is counted as an attacker until they play a called
 * card. So a still-hidden friend sees the alpha team as the opposition, right
 * up until they jump on it. Same public facts as teamOf, so nothing leaks. */
export const sideSoFar = ({ playerUuid, alphaUuid = '', revealedFriends = [] }) => {
    if (!alphaUuid) return '';
    return playerUuid === alphaUuid || revealedFriends.includes(playerUuid) ? 'alpha' : 'attacker';
};
