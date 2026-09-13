import { useEffect, useRef, useState } from 'react';
import { SOCKET_EVENTS } from '../api/events';
import { PHASE } from '../constants/phases';

const IDLE = { status: 'idle', message: '' };

/** How long a queued play waits once the turn arrives, so the table can see it happen. */
export const AUTO_PLAY_DELAY_MS = 2000;

/* Picking your answer to a trick before your turn comes round.
 *
 * As soon as enough cards are picked to answer the lead, the server is asked
 * whether they would be legal. The rules live there, and a guess made here that
 * disagreed with it would be worse than no guess at all. A legal pick can then
 * be queued, and it is played the moment the turn arrives.
 *
 * Only a follow is checked. Its legality depends on nothing but the lead and
 * your own hand, so an early answer still holds when the turn comes — see
 * handle_check_play in the backend's Main.py.
 *
 * `trickKey` names the question a pick is answering: a new lead or a changed
 * hand makes the old answer, and anything queued on it, about something else. */
export const usePlaySelection = ({ socket, connected, view, selection, emit, gameCode, playerUuid, trickKey }) => {
    const [check, setCheck] = useState(IDLE);
    // The pick that was queued, by key, so a queue can never outlive the exact
    // cards and trick it was made for.
    const [queuedFor, setQueuedFor] = useState(null);
    const latestRequest = useRef(0);

    const lead = view.leading_hand_of_subround || [];
    const hand = view.player_hand || [];
    const following = view.game_event_state === PHASE.ROUND_STARTED && lead.length > 0;
    const complete = following && selection.count === lead.length;
    const pickKey = `${trickKey}|${[...selection.indices].sort((a, b) => a - b).join(',')}`;
    const cards = selection.indices
        .map(index => hand[index])
        .filter(Boolean)
        .map(({ suit, rank }) => ({ suit, rank }));

    /* Every change to the pick un-queues it and asks again. Un-queueing is on
     * purpose rather than carried over: a player who changes their mind should
     * have to say they are happy with the new cards too. */
    useEffect(() => {
        latestRequest.current += 1;
        setQueuedFor(null);
        if (!complete || !socket || !connected) {
            setCheck(IDLE);
            return;
        }
        setCheck({ status: 'checking', message: '' });
        socket.emit(SOCKET_EVENTS.CHECK_PLAY, {
            game_code: gameCode,
            player_uuid: playerUuid,
            cards,
            request_id: latestRequest.current,
        });
        // `cards` is left out: it is derived from pickKey, which is what changes.
    }, [pickKey, complete, socket, connected, gameCode, playerUuid]);

    // Answers to a pick that has since changed are dropped, not shown.
    useEffect(() => {
        if (!socket) return undefined;
        const handleAnswer = (data) => {
            if (!data || data.request_id !== latestRequest.current) return;
            setCheck(data.legal
                ? { status: 'legal', message: '' }
                : { status: 'illegal', message: data.message || 'That play is not allowed.' });
        };
        socket.on(SOCKET_EVENTS.PLAY_CHECK, handleAnswer);
        return () => socket.off(SOCKET_EVENTS.PLAY_CHECK, handleAnswer);
    }, [socket]);

    const queued = queuedFor === pickKey;
    const canQueue = !view.my_turn && check.status === 'legal';

    /* The turn arriving plays the queue, once, after a short pause. Without the
     * pause a table of queued players empties a trick faster than anyone can
     * follow it. Cancelling, changing the pick or losing the connection during
     * the pause stops the play. The server still checks the play as it would
     * any other, so this can never get past a rule. */
    useEffect(() => {
        if (!queued || !view.my_turn || !connected) return undefined;
        const timer = setTimeout(() => {
            setQueuedFor(null);
            emit(SOCKET_EVENTS.PLAY_CARDS, { cards });
        }, AUTO_PLAY_DELAY_MS);
        return () => clearTimeout(timer);
    }, [queued, view.my_turn, connected]);

    return {
        status: check.status,
        message: check.message,
        queued,
        canQueue,
        queue: () => { if (canQueue) setQueuedFor(pickKey); },
        // Cancelling drops the pick too: the player is starting over, not
        // editing, and leftover selected cards would read as still queued.
        cancel: () => {
            setQueuedFor(null);
            selection.clear();
        },
    };
};
