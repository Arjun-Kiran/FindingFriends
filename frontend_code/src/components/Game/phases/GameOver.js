import { LEVEL_LABELS } from '../../../constants/cards';

const GameOver = ({ view, onLeaveGame }) => {
    const players = view.player_list || [];
    const levels = view.player_levels || {};
    const winner = players.find(player => player.uuid === view.game_winner);

    return (
        <div className="result-card game-over">
            <h3>Game Over!</h3>
            <p className="game-over-headline">
                {winner ? `${winner.name} has passed Ace and wins the game!` : 'A player has won!'}
            </p>

            <h4>Final Levels</h4>
            <div className="level-chips">
                {players.map(player => (
                    <span
                        key={player.uuid}
                        className={`level-chip${player.uuid === view.game_winner ? ' winner' : ''}`}
                    >
                        {player.name}: Lv {LEVEL_LABELS[levels[player.uuid]] || levels[player.uuid] || '?'}
                    </span>
                ))}
            </div>

            {onLeaveGame && (
                <button className="btn btn-primary btn-inline btn-spaced" onClick={onLeaveGame}>
                    Back to Home
                </button>
            )}
        </div>
    );
};

export default GameOver;
