import { useGameSocket } from '../../hooks/useGameSocket';
import { useCardSelection } from '../../hooks/useCardSelection';
import { phaseFor } from './phases';
import GameHeader from './GameHeader';
import PlayersBar from './PlayersBar';
import ErrorBanner from './ErrorBanner';
import TrickArea from './TrickArea';
import Hand from './Hand';
import { CalledCardsStrip, RevealedFriendsStrip, ScoresBar } from './MetaStrips';

/* Layout and phase routing. Everything phase-specific lives in ./phases. */
const Game = ({ sessionInfo, initialGameState, socket: externalSocket, onLeaveGame }) => {
    const gameCode = sessionInfo.game_code;
    const playerUuid = sessionInfo.user_uuid;

    const { socket, gameState, errorMessage, setErrorMessage } = useGameSocket({
        gameCode,
        playerUuid,
        externalSocket,
        initialState: initialGameState,
    });

    const view = gameState || {};
    const selection = useCardSelection(gameState);
    const { Panel, handRules } = phaseFor(view.game_event_state);

    const emit = (event, payload = {}) => {
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
            />
            <ErrorBanner message={errorMessage} onDismiss={() => setErrorMessage('')} />

            <CalledCardsStrip view={view} />
            <TrickArea cards={view.cards_in_active_pile} />

            {Panel && (
                <Panel view={view} emit={emit} selection={selection} onLeaveGame={onLeaveGame} />
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
