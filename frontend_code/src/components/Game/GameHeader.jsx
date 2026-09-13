import { SUIT_SYMBOLS, LEVEL_LABELS } from '../../constants/cards';
import { phaseLabel, phaseClass } from '../../constants/phases';
import { Icon } from '../Emoji';
import { ROLE_EMOJI } from '../../constants/emoji';
import { useCopyState } from '../../hooks/useCopyState';

const COPY_LABELS = { idle: 'Copy', copied: 'Copied!', failed: 'Copy failed' };

const GameHeader = ({ view, gameCode, onLeaveGame }) => {
    /* The code is what someone needs to watch the game, or to ask for a seat
     * from the next round (HR-8), so it can be shared from mid-game and not
     * only from the lobby. */
    const [copyState, copyCode] = useCopyState(gameCode);
    const phase = view.game_event_state || '';
    const trumpSuit = view.declare_trump && view.declare_trump.suit;
    const trumpRank = view.declare_trump && view.declare_trump.rank;
    const myLevel = view.my_level;

    return (
        <div className="game-header">
            <div className="game-header-left">
                <h2>Finding Friends</h2>
                <span className="game-code-small">Game: {gameCode}</span>
                <button
                    type="button"
                    className="btn-copy btn-copy-small"
                    onClick={copyCode}
                    title={copyState === 'failed'
                        ? 'Could not reach the clipboard. Select the code and copy it yourself.'
                        : 'Copy the game code to share it'}
                >
                    {COPY_LABELS[copyState]}
                </button>
            </div>
            <div className="game-header-right">
                <span className={`phase-badge ${phaseClass(phase)}`}>{phaseLabel(phase)}</span>
                {trumpSuit && (
                    <div className="trump-info">Trump: {trumpRank} of {SUIT_SYMBOLS[trumpSuit] || trumpSuit}</div>
                )}
                {myLevel ? (
                    <div className="my-level">Your Level: {LEVEL_LABELS[myLevel] || myLevel}</div>
                ) : null}
                {view.is_alpha && (
                    <div className="alpha-badge">
                        <Icon emoji={ROLE_EMOJI.ALPHA} label="Alpha player" />You are the Alpha
                    </div>
                )}
                {view.is_watcher && (
                    <div className="watching-badge">
                        <Icon emoji={ROLE_EMOJI.WATCHER} label="Watching" />Watching
                    </div>
                )}
                {onLeaveGame && (
                    <button className="btn-leave" onClick={onLeaveGame}>
                        {view.is_watcher ? 'Stop Watching' : 'Leave Game'}
                    </button>
                )}
            </div>
        </div>
    );
};

export default GameHeader;
