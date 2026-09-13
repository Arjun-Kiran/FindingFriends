import { SOCKET_EVENTS } from '../../api/events';
import { useGameSocket } from '../../hooks/useGameSocket';
import { useCardSelection } from '../../hooks/useCardSelection';
import { useHandOrder } from '../../hooks/useHandOrder';
import { usePlaySelection } from '../../hooks/usePlaySelection';
import { PHASE } from '../../constants/phases';
import { teamOf } from '../../utils/teams';
import Notifications from './Notifications';
import BigNotification from './BigNotification';
import { phaseFor } from './phases';
import ConnectionBanner from '../ConnectionBanner';
import GameHeader from './GameHeader';
import PlayersBar from './PlayersBar';
import ErrorBanner from './ErrorBanner';
import TrickArea from './TrickArea';
import Hand from './Hand';
import { CalledCardsStrip, ScoresBar } from './MetaStrips';
import SeatPanel from './SeatPanel';
import WatcherPanel from './WatcherPanel';
import { useServerNow } from '../../hooks/useServerNow';

/* A stable empty hand, so the arrangement below is not rebuilt every render
 * on the screens that have no hand yet. */
const EMPTY_HAND = [];

/* Layout and phase routing. Everything phase-specific lives in ./phases. */
const Game = ({ sessionInfo, initialGameState, socket: externalSocket, onLeaveGame, onSessionInvalid }) => {
    const gameCode = sessionInfo.game_code;
    const playerUuid = sessionInfo.user_uuid;

    const { socket, connected, gameState, errorMessage, setErrorMessage } = useGameSocket({
        gameCode,
        playerToken: sessionInfo.player_token,
        externalSocket,
        initialState: initialGameState,
        onSessionInvalid,
    });

    const view = gameState || {};
    const hand = view.player_hand || EMPTY_HAND;
    const isWatcher = Boolean(view.is_watcher);
    /* Who this browser is at the table. Read off the view rather than the saved
     * session: the host can seat a watcher mid-game, and from then on the same
     * token speaks for a seat with a different uuid (HR-8). */
    const myUuid = view.uuid || playerUuid;
    /* What a pick in the hand is an answer to. During a round that is the lead
     * and the hand it is picked from — not the whole game state, which changes
     * every time anyone plays and would wipe cards picked ahead of your turn.
     * Every trick changes your hand, so a new trick always starts fresh. */
    const trickKey = view.game_event_state === PHASE.ROUND_STARTED
        ? JSON.stringify([view.leading_hand_of_subround || [], hand])
        : null;
    const selection = useCardSelection(trickKey === null ? gameState : trickKey);
    /* How the hand is laid out is the player's business, not the server's, so
     * it lives here and never reaches a payload. See utils/handOrder.js. */
    const handOrder = useHandOrder(hand, { gameCode, playerUuid: myUuid, trump: view.declare_trump });
    const { Panel, handRules, handAction, handNote, handStatus } = phaseFor(view.game_event_state);

    /* Which side to show a player as, worked out once and handed to everything
     * that draws one. Sides are the game's central secret, so the rule lives in
     * one place — see utils/teams.js. */
    const teamFor = (uuid) => teamOf({
        playerUuid: uuid,
        alphaUuid: view.alpha_uuid,
        revealedFriends: view.revealed_friends || [],
        allFriendsFound: view.all_friends_found,
    });

    /* The one path for anything that has to reach the server. While the socket
     * is down it refuses instead of dropping the action silently — socket.io
     * would buffer it and replay it into a game that has since moved on. */
    const emit = (event, payload = {}) => {
        if (!connected) {
            setErrorMessage('Not connected to the server — waiting to reconnect.');
            return;
        }
        if (!socket) return;
        socket.emit(event, { game_code: gameCode, player_uuid: myUuid, ...payload });
    };

    /* Checking picked cards with the server, and playing a queued pick when
     * the turn arrives. See hooks/usePlaySelection.js. */
    const preselect = usePlaySelection({
        socket, connected, view, selection, emit, gameCode, playerUuid: myUuid, trickKey,
    });

    /* Say goodbye to the table on the way out, so the others see "left the
     * game" rather than waiting on a reconnect that is never coming.
     *
     * Never blocks leaving on the socket: if the connection is already down
     * there is nobody to tell, and trapping the player in a dead game would be
     * far worse than a missing notification. */
    const leaveGame = () => {
        if (socket && connected) {
            socket.emit(SOCKET_EVENTS.LEAVE_GAME, {
                game_code: gameCode,
                player_uuid: myUuid,
            });
        }
        if (onLeaveGame) onLeaveGame();
    };

    /* HR-8. Ticks only while there is a countdown on screen to move. */
    const vacancies = view.seat_vacancies || {};
    const serverNow = useServerNow(
        view.server_time,
        Object.keys(vacancies).length > 0 || Boolean(view.room_closes_at)
    );
    const offer = (view.seat_requests || []).find(request => request.watcher_uuid === view.uuid);
    const takeSeat = (seatUuid) => emit(SOCKET_EVENTS.VOLUNTEER_FOR_SEAT, { seat_uuid: seatUuid });

    return (
        <div className="game-container">
            <GameHeader view={view} gameCode={gameCode} onLeaveGame={leaveGame} />

            {/* Scores sit with the header rather than down by the hand: they are
              * something you glance up at, not something you act on. */}
            <ScoresBar view={view} />

            <PlayersBar
                players={view.player_list}
                currentPlayer={view.current_player}
                myUuid={myUuid}
                disconnected={view.disconnected_players}
                alphaUuid={view.alpha_uuid}
                /* Only while the totals are hidden. The server sends who leads
                 * either way — it is the one thing about the score a blind
                 * table still gets — but with the numbers up there is nothing
                 * left for a flame to say. */
                onFire={view.scores_hidden ? view.top_scorer_uuids : []}
                teamFor={teamFor}
                vacancies={vacancies}
                graceSeconds={view.seat_grace_seconds}
                serverNow={serverNow}
                openSeats={view.open_seats}
                onTakeSeat={isWatcher ? takeSeat : null}
                offeredSeat={offer ? offer.seat_uuid : ''}
            />
            <ConnectionBanner connected={connected} />
            <ErrorBanner message={errorMessage} onDismiss={() => setErrorMessage('')} />
            <SeatPanel view={view} emit={emit} serverNow={serverNow} />

            <Notifications events={view.events} players={view.player_list} />

            {/* Over the board rather than in the layout — it covers the table
              * for a moment and takes no space. Everything it says is also in
              * the feed above or the phase panel below. */}
            <BigNotification
                events={view.events}
                myTurn={view.my_turn}
                players={view.player_list}
            />

            <CalledCardsStrip view={view} />

            {/* Above the trick, because during a round this is the turn
              * indicator — what you are being asked to do comes before what is
              * already on the table. Every other phase draws its panel here
              * too, and in those the trick area is empty anyway. */}
            {Panel && (
                /* Dimmed rather than click-blocked while offline: panels also
                 * hold local buttons like "Back to Home", which still work. */
                <div className={connected ? 'phase-panel' : 'phase-panel is-offline'}>
                    <Panel view={view} emit={emit} selection={selection} preselect={preselect} onLeaveGame={leaveGame} />
                </div>
            )}

            <TrickArea
                cards={view.cards_in_active_pile}
                playedBy={view.active_pile_player_uuids}
                players={view.player_list}
                winningUuid={view.winning_player_of_round && view.winning_player_of_round.uuid}
                teamFor={teamFor}
            />

            {isWatcher ? (
                <WatcherPanel view={view} emit={emit} />
            ) : (
                <Hand
                    cards={hand}
                    rules={handRules ? handRules(view) : null}
                    selection={selection}
                    order={handOrder.order}
                    onMove={handOrder.move}
                    onSort={handOrder.sort}
                    trump={view.declare_trump}
                    playable={view.playable_hand_cards}
                    action={handAction ? handAction({ view, emit, selection, preselect }) : null}
                    note={handNote ? handNote(view) : ''}
                    status={handStatus ? handStatus({ view, preselect }) : null}
                />
            )}
        </div>
    );
};

export default Game;
