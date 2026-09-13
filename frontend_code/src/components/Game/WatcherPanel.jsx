import { SOCKET_EVENTS } from '../../api/events';
import { PHASE } from '../../constants/phases';
import { ROLE_EMOJI } from '../../constants/emoji';
import { Icon } from '../Emoji';

/* Where a player's hand would be, for someone watching (HR-8).
 *
 * Says what they are looking at — the table, and nobody's cards — and what
 * they can do about it: offer for a free seat from the players bar, or ask to
 * play from the next round. Only the host can say yes, so once they have asked
 * it says that too, and who the host is. */
const WatcherPanel = ({ view, emit }) => {
    const players = view.player_list || [];
    const nameOf = (uuid) => (players.find(player => player.uuid === uuid) || {}).name || 'a player';
    const host = players.find(player => player.uuid === view.host_uuid);
    const hostLabel = host ? `the host (${host.name})` : 'the host';
    const request = (view.seat_requests || []).find(candidate => candidate.watcher_uuid === view.uuid);
    const freeSeats = Object.keys(view.seat_vacancies || {});

    const takeBack = (
        <button
            type="button"
            className="btn btn-secondary btn-inline"
            onClick={() => emit(SOCKET_EVENTS.WITHDRAW_SEAT_REQUEST)}
        >
            Take back
        </button>
    );

    let status = null;
    if (request && request.seat_uuid) {
        status = (
            <p className="watcher-status">
                {`You offered to take over ${nameOf(request.seat_uuid)}'s seat. Waiting for ${hostLabel} to say yes.`}
                {' '}{takeBack}
            </p>
        );
    } else if (request && request.approved) {
        status = (
            <p className="watcher-status">
                {'The host said yes: you join when the next round starts.'}
                {' '}{takeBack}
            </p>
        );
    } else if (request) {
        status = (
            <p className="watcher-status">
                {`You asked to play from the next round. Waiting for ${hostLabel} to say yes.`}
                {' '}{takeBack}
            </p>
        );
    } else if (view.game_event_state !== PHASE.GAME_ENDED) {
        status = (
            <>
                {freeSeats.length > 0 && (
                    <p className="watcher-status">
                        A seat is free. Press “Take seat” under it in the players bar to offer to play it.
                    </p>
                )}
                <button
                    type="button"
                    className="btn btn-primary btn-inline"
                    onClick={() => emit(SOCKET_EVENTS.ASK_TO_JOIN)}
                >
                    Ask to play from the next round
                </button>
            </>
        );
    }

    return (
        <div className="hand-area watcher-panel">
            <h4><Icon emoji={ROLE_EMOJI.WATCHER} label="Watching" />You are watching</h4>
            <p className="watcher-note">You can see the table, but not anyone's hand.</p>
            {status}
        </div>
    );
};

export default WatcherPanel;
