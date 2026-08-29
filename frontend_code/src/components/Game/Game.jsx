import { SOCKET_EVENTS } from '../../api/events';
import { useGameSocket } from '../../hooks/useGameSocket';
import { useCardSelection } from '../../hooks/useCardSelection';
import { useHandOrder } from '../../hooks/useHandOrder';
import Notifications from './Notifications';
import { phaseFor } from './phases';
import ConnectionBanner from '../ConnectionBanner';
import GameHeader from './GameHeader';
import PlayersBar from './PlayersBar';
import ErrorBanner from './ErrorBanner';
import TrickArea from './TrickArea';
import Hand from './Hand';
import { CalledCardsStrip, RevealedFriendsStrip, ScoresBar } from './MetaStrips';

/* A stable empty hand, so the arrangement below is not rebuilt every render
 * on the screens that have no hand yet. */
const EMPTY_HAND = [];

/* Layout and phase routing. Everything phase-specific lives in ./phases. */
const Game = ({ sessionInfo, initialGameState, socket: externalSocket, onLeaveGame, onSessionInvalid }) => {
    const gameCode = sessionInfo.game_code;
    const playerUuid = sessionInfo.user_uuid;

    const { socket, connected, gameState, errorMessage, setErrorMessage } = useGameSocket({
        gameCode,
        playerUuid,
        externalSocket,
        initialState: initialGameState,
        onSessionInvalid,
    });

    const view = gameState || {};
    const hand = view.player_hand || EMPTY_HAND;
    const selection = useCardSelection(gameState);
    /* How the hand is laid out is the player's business, not the server's, so
     * it lives here and never reaches a payload. See utils/handOrder.js. */
    const handOrder = useHandOrder(hand, { gameCode, playerUuid, trump: view.declare_trump });
    const { Panel, handRules } = phaseFor(view.game_event_state);

    /* The one path for anything that has to reach the server. While the socket
     * is down it refuses instead of dropping the action silently — socket.io
     * would buffer it and replay it into a game that has since moved on. */
    const emit = (event, payload = {}) => {
        if (!connected) {
            setErrorMessage('Not connected to the server — waiting to reconnect.');
            return;
        }
        if (!socket) return;
        socket.emit(event, { game_code: gameCode, player_uuid: playerUuid, ...payload });
    };

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
                player_uuid: playerUuid,
            });
        }
        if (onLeaveGame) onLeaveGame();
    };

    return (
        <div className="game-container">
            <GameHeader view={view} gameCode={gameCode} onLeaveGame={leaveGame} />
            <PlayersBar
                players={view.player_list}
                currentPlayer={view.current_player}
                myUuid={playerUuid}
                disconnected={view.disconnected_players}
                alphaUuid={view.alpha_uuid}
                revealedFriends={view.revealed_friends || []}
            />
            <ConnectionBanner connected={connected} />
            <ErrorBanner message={errorMessage} onDismiss={() => setErrorMessage('')} />

            <Notifications events={view.events} players={view.player_list} />

            <CalledCardsStrip view={view} />
            <TrickArea
                cards={view.cards_in_active_pile}
                playedBy={view.active_pile_player_uuids}
                players={view.player_list}
                winningUuid={view.winning_player_of_round && view.winning_player_of_round.uuid}
            />

            {Panel && (
                /* Dimmed rather than click-blocked while offline: panels also
                 * hold local buttons like "Back to Home", which still work. */
                <div className={connected ? 'phase-panel' : 'phase-panel is-offline'}>
                    <Panel view={view} emit={emit} selection={selection} onLeaveGame={leaveGame} />
                </div>
            )}

            <RevealedFriendsStrip view={view} />
            <ScoresBar view={view} />

            <Hand
                cards={hand}
                rules={handRules ? handRules(view) : null}
                selection={selection}
                order={handOrder.order}
                onMove={handOrder.move}
                onSort={handOrder.sort}
                trump={view.declare_trump}
                playable={view.playable_hand_cards}
            />
        </div>
    );
};

export default Game;
