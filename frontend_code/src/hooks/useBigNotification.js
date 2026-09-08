import { useEffect, useRef, useState } from 'react';

/* How long a banner stays up. The fade is CSS; this is what removes the
 * element, so the two have to agree — see .big-notification in App.css. */
export const BANNER_MS = 2400;

/** How many players' plays one banner will name before the rest are left to
 *  the feed. Two short lines read in the same glance one does; three do not. */
export const MAX_EVENT_LINES = 2;

/* Which happening wins the space when more land at once than will fit.
 *
 * Ordered by how much it changes the game rather than how rare it is: a friend
 * revealing themselves redraws the teams and is the one thing here you cannot
 * work out later from the board. Anything not listed sorts last, so a clause
 * added on the server shows up without needing a matching change here. */
const PRIORITY = [
    'friend-revealed',
    'trick-won',
    'hand-play',
    'trump-declared',
    'friends-called',
];

const rankOf = (event) => {
    const found = PRIORITY.indexOf(event);
    return found === -1 ? PRIORITY.length : found;
};

/** 'a and b', 'a, b and c' — the clauses of one player under one name. */
const joinClauses = (clauses) => {
    if (clauses.length === 1) return clauses[0];
    return `${clauses.slice(0, -1).join(', ')} and ${clauses[clauses.length - 1]}`;
};

/* One line per player, their clauses stitched together under their one name.
 *
 * Grouping by player is what makes "Bob led with a tractor and won the trick"
 * possible; it is also why lines exist at all, because the player who reveals
 * themselves as a friend is whoever played the called card and need not be the
 * one who takes the trick. Those two cannot share a sentence. */
const composeLines = (events, players, turnJustCame) => {
    const byPlayer = new Map();
    events.forEach((event) => {
        const group = byPlayer.get(event.player_uuid) || [];
        group.push(event);
        byPlayer.set(event.player_uuid, group);
    });

    const lines = [];
    byPlayer.forEach((group, uuid) => {
        // An event about someone who has since left the table has no name and
        // no avatar to put on it. Not worth covering the board for — the feed
        // still carries it, name and all.
        const player = (players || []).find(candidate => candidate.uuid === uuid);
        if (!player) return;
        lines.push({
            id: group[0].uuid,
            player,
            text: joinClauses(group.map(event => event.clause)),
            rank: Math.min(...group.map(event => rankOf(event.event))),
        });
    });

    lines.sort((a, b) => a.rank - b.rank);
    const kept = lines.slice(0, MAX_EVENT_LINES);

    /* Always kept, never cut by the cap above: it is the only line that asks
     * the player to do something, and it is about them rather than the table. */
    if (turnJustCame) kept.push({ id: 'your-turn', player: null, text: 'Your turn' });

    return kept;
};

/* The banner that covers the board for a moment to call out a big play.
 *
 * Reads the same event stream the corner feed does, but only the events
 * carrying a `clause` — the server decides what is big, so that judgement is
 * not made in two places. The one thing not in the stream is whose turn it is:
 * events go to the whole table identically and this is addressed to one
 * player, so it is worked out here from `myTurn` turning true.
 */
export const useBigNotification = ({ events, myTurn, players }) => {
    const [banner, setBanner] = useState(null);
    /* Which events have already had their moment. Rebuilt from the events on
     * hand each time rather than grown, so it stays the size of the feed —
     * and so a reconnect, which re-pushes the whole state unchanged, does not
     * replay the last banner. */
    const announcedRef = useRef(null);
    const wasMyTurnRef = useRef(false);
    const keyRef = useRef(0);

    useEffect(() => {
        const list = events || [];

        /* First look at this table: everything already in the feed is history,
         * not news. Without this, opening the board mid-game would fire a
         * banner for whatever happened before you got there. */
        const firstLook = announcedRef.current === null;
        const announced = firstLook ? new Set() : announcedRef.current;
        const fresh = firstLook
            ? []
            : list.filter(event => event.clause && !announced.has(event.uuid));
        announcedRef.current = new Set(list.map(event => event.uuid));

        /* Not skipped on a first look. Loading straight into your own turn is
         * exactly when you need telling, and the ref only resets on a remount
         * — a reconnect keeps it, so this cannot fire twice for one turn. */
        const turnJustCame = Boolean(myTurn) && !wasMyTurnRef.current;
        wasMyTurnRef.current = Boolean(myTurn);

        const lines = composeLines(fresh, players, turnJustCame);
        if (lines.length === 0) return;

        // A new banner replaces whatever is up, rather than queueing behind it:
        // two seconds is already a long time to cover the table.
        keyRef.current += 1;
        setBanner({ key: keyRef.current, lines });
    }, [events, myTurn, players]);

    useEffect(() => {
        if (!banner) return undefined;
        const timer = setTimeout(() => setBanner(null), BANNER_MS);
        return () => clearTimeout(timer);
    }, [banner]);

    return banner;
};
