import { useState } from 'react';
import { SOCKET_EVENTS } from '../../api/events';
import { LEVEL_LABELS, RANK_VALUES } from '../../constants/cards';
import { STATUS_EMOJI } from '../../constants/emoji';
import { formatCountdown } from '../../utils/countdown';
import { Icon } from '../Emoji';

/* Two through Ace, as level values — the levels a joiner can start on. */
const STARTING_LEVELS = Array.from(
    { length: RANK_VALUES.ACE - RANK_VALUES.TWO + 1 },
    (_, offset) => RANK_VALUES.TWO + offset
);

const openSeatsSentence = (names) => (names.length === 1
    ? `${names[0]}'s seat is open.`
    : `Seats are open: ${names.join(', ')}.`);

/* One watcher's request, as the host sees it. */
const SeatRequestRow = ({ request, watcherName, seatName, emit }) => {
    const [level, setLevel] = useState(RANK_VALUES.TWO);
    const approve = (extra = {}) => emit(SOCKET_EVENTS.APPROVE_SEAT_REQUEST, {
        watcher_uuid: request.watcher_uuid, ...extra,
    });
    const decline = () => emit(SOCKET_EVENTS.DECLINE_SEAT_REQUEST, { watcher_uuid: request.watcher_uuid });

    if (request.seat_uuid) {
        return (
            <li className="seat-request">
                {/* Says it cannot be taken back, because it cannot: the
                    volunteer sits down the moment the host approves, even if
                    the player still has time left to come back. */}
                <span>{`${watcherName} wants to take over ${seatName}'s seat, hand and all. Approving seats them straight away.`}</span>
                <button type="button" className="btn btn-primary btn-inline" onClick={() => approve()}>Approve</button>
                <button type="button" className="btn btn-secondary btn-inline" onClick={decline}>Decline</button>
            </li>
        );
    }

    if (request.approved) {
        return (
            <li className="seat-request">
                <span>{`${watcherName} joins when the next round starts, on level ${LEVEL_LABELS[request.level] || request.level}.`}</span>
                <button type="button" className="btn btn-secondary btn-inline" onClick={decline}>Cancel</button>
            </li>
        );
    }

    return (
        <li className="seat-request">
            <span>{`${watcherName} wants to play from the next round.`}</span>
            <label>
                Starting level{' '}
                <select
                    aria-label={`${watcherName}'s starting level`}
                    value={level}
                    onChange={event => setLevel(Number(event.target.value))}
                >
                    {STARTING_LEVELS.map(value => (
                        <option key={value} value={value}>{LEVEL_LABELS[value]}</option>
                    ))}
                </select>
            </label>
            <button type="button" className="btn btn-primary btn-inline" onClick={() => approve({ level })}>Approve</button>
            <button type="button" className="btn btn-secondary btn-inline" onClick={decline}>Decline</button>
        </li>
    );
};

/* HR-8, as the table sees it: a room running short of players, a round held
 * up by an empty seat, and — for the host alone — the watchers asking to play.
 *
 * Renders nothing when none of those is true, which is almost always. */
const SeatPanel = ({ view, emit, serverNow }) => {
    const players = view.player_list || [];
    const watchers = view.watchers || [];
    const requests = view.seat_requests || [];
    const playerName = (uuid) => (players.find(player => player.uuid === uuid) || {}).name || 'A player';
    const watcherName = (uuid) => (watchers.find(watcher => watcher.uuid === uuid) || {}).name || 'A watcher';
    const host = players.find(player => player.uuid === view.host_uuid);
    const openNames = (view.open_seats || []).map(playerName);

    const closing = view.room_closes_at ? (
        <div className="info-panel room-closing" role="status">
            <Icon emoji={STATUS_EMOJI.WARNING} label="Warning" />
            {`Fewer than 5 players are connected. This room closes in ${formatCountdown(view.room_closes_at - serverNow)} unless 5 are back.`}
        </div>
    ) : null;

    let heldUp = null;
    if (view.round_held_up && openNames.length > 0) {
        heldUp = view.hosting ? (
            <div className="seat-held-up">
                <p>
                    <Icon emoji={STATUS_EMOJI.SEAT_OPEN} label="Seat open" />
                    {`${openSeatsSentence(openNames)} Approve a watcher to take over, or end the round as a draw — nobody moves up.`}
                </p>
                <button
                    type="button"
                    className="btn btn-danger btn-inline"
                    onClick={() => emit(SOCKET_EVENTS.END_ROUND_AS_DRAW)}
                >
                    End round as a draw
                </button>
            </div>
        ) : (
            <p className="seat-held-up">
                <Icon emoji={STATUS_EMOJI.SEAT_OPEN} label="Seat open" />
                {`${openSeatsSentence(openNames)} Waiting for ${host ? `the host (${host.name})` : 'the host'} to hand it to a watcher or end the round.`}
            </p>
        );
    }

    const hostRequests = view.hosting && requests.length > 0 ? (
        <ul className="seat-requests">
            {requests.map(request => (
                <SeatRequestRow
                    key={request.watcher_uuid}
                    request={request}
                    watcherName={watcherName(request.watcher_uuid)}
                    seatName={playerName(request.seat_uuid)}
                    emit={emit}
                />
            ))}
        </ul>
    ) : null;

    if (!closing && !heldUp && !hostRequests) return null;

    return (
        <>
            {closing}
            {(heldUp || hostRequests) && (
                <div className="info-panel seat-panel">
                    {heldUp}
                    {hostRequests}
                </div>
            )}
        </>
    );
};

export default SeatPanel;
