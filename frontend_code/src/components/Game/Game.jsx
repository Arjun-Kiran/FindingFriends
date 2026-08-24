import { useGameSocket } from '../../hooks/useGameSocket';
import { useCardSelection } from '../../hooks/useCardSelection';
import { useEventToast } from '../../hooks/useEventToast';
import { phaseFor } from './phases';
import ConnectionBanner from '../ConnectionBanner';
import GameHeader from './GameHeader';
import PlayersBar from './PlayersBar';
import ErrorBanner from './ErrorBanner';
import TrickArea from './TrickArea';
import Hand from './Hand';
import { CalledCardsStrip, RevealedFriendsStrip, ScoresBar } from './MetaStrips';

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
    const selection = useCardSelection(gameState);
    const toastMessage = useEventToast(view.events);
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

    return (
        <div className="game-container">
            <GameHeader view={view} gameCode={gameCode} onLeaveGame={onLeaveGame} />
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

            {toastMessage && (
                <div className="toast-notification">{toastMessage}</div>
            )}

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
                    <Panel view={view} emit={emit} selection={selection} onLeaveGame={onLeaveGame} />
                </div>
            )}

            <RevealedFriendsStrip view={view} />
            <ScoresBar view={view} />

            <Hand
                cards={view.player_hand}
                rules={handRules ? handRules(view) : null}
                selection={selection}
            />
        </div>
    );
};

export default Game;
