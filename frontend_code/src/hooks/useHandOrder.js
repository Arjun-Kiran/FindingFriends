import { useCallback, useEffect, useMemo, useState } from 'react';
import { cardKey, moveWithin, reconcile, sortedOrder } from '../utils/handOrder';

/* Remembers how a player has arranged their hand.
 *
 * Held as card keys rather than positions, so the arrangement outlives the hand
 * it was made on: play three cards and the rest stay put, reload the page and
 * they are still where you left them. See utils/handOrder.js for why a card
 * cannot simply be given an id.
 *
 * Scoped per game and per player — two games in two tabs must not read each
 * other's arrangement, and neither should the next game in this one. */
const storageKey = (gameCode, playerUuid) =>
    `findingFriendsHandOrder:${gameCode}:${playerUuid}`;

/* Storage is a convenience here, never a requirement: private windows and full
 * quotas both throw, and a hand in dealt order is a perfectly playable hand. */
const readKeys = (key) => {
    if (!key) return [];
    try {
        const saved = JSON.parse(localStorage.getItem(key));
        return Array.isArray(saved) ? saved.filter(entry => typeof entry === 'string') : [];
    } catch {
        return [];
    }
};

const writeKeys = (key, keys) => {
    if (!key) return;
    try {
        localStorage.setItem(key, JSON.stringify(keys));
    } catch {
        /* Arrangement lives for this session only. Nothing else breaks. */
    }
};

export const useHandOrder = (hand = [], { gameCode, playerUuid, trump } = {}) => {
    const key = gameCode && playerUuid ? storageKey(gameCode, playerUuid) : null;
    const [keys, setKeys] = useState(() => readKeys(key));

    /* The arrangement is derived, not stored: a hand arriving from the server
     * is laid out by re-reading the same keys, so there is no moment where the
     * order and the hand disagree.
     *
     * With no arrangement yet, the hand is sorted. The server sends it in the
     * order the engine happens to hold it — laying it out is entirely the
     * client's job — and nobody wants to read an unsorted hand. Once the player
     * has arranged it themselves that stops: their order wins, and new cards go
     * on the end rather than being tidied away somewhere they did not put them. */
    const order = useMemo(
        () => (keys.length ? reconcile(keys, hand) : sortedOrder(hand, trump)),
        [keys, hand, trump]
    );

    useEffect(() => {
        writeKeys(key, keys);
    }, [key, keys]);

    const remember = useCallback(
        (indices) => setKeys(indices.map(index => cardKey(hand[index]))),
        [hand]
    );

    return {
        order,
        /** Move the card at display position `from` to sit before position `to`. */
        move: useCallback((from, to) => remember(moveWithin(order, from, to)), [order, remember]),
        /** Lay the hand out trumps first, then by suit and rank. */
        sort: useCallback(() => remember(sortedOrder(hand, trump)), [hand, trump, remember]),
    };
};
