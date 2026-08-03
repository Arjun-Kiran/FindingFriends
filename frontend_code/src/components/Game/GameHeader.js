import { SUIT_SYMBOLS, LEVEL_LABELS } from '../../constants/cards';
import { phaseLabel, phaseClass } from '../../constants/phases';

const GameHeader = ({ view, gameCode, onLeaveGame }) => {
    const phase = view.game_event_state || '';
    const trumpSuit = view.declare_trump && view.declare_trump.suit;
    const trumpRank = view.declare_trump && view.declare_trump.rank;
    const myLevel = view.my_level;

    return (
        <div className="game-header">
            <div className="game-header-left">
                <h2>Finding Friends</h2>
                <span className="game-code-small">Game: {gameCode}</span>
            </div>
            <div className="game-header-right">
                <span className={`phase-badge ${phaseClass(phase)}`}>{phaseLabel(phase)}</span>
                {trumpSuit && (
                    <div className="trump-info">Trump: {trumpRank} of {SUIT_SYMBOLS[trumpSuit] || trumpSuit}</div>
                )}
                {myLevel ? (
                    <div className="my-level">Your Level: {LEVEL_LABELS[myLevel] || myLevel}</div>
                ) : null}
                {view.is_alpha && <div className="alpha-badge">You are the Alpha</div>}
                {onLeaveGame && <button className="btn-leave" onClick={onLeaveGame}>Leave Game</button>}
            </div>
        </div>
    );
};

export default GameHeader;
