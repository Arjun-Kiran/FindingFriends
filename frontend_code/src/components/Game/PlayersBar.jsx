const PlayersBar = ({ players = [], currentPlayer, myUuid, disconnected = [] }) => (
    <div className="players-bar">
        {players.map((player, idx) => {
            const isCurrent = currentPlayer && currentPlayer.uuid === player.uuid;
            const isMe = player.uuid === myUuid;
            // Their seat is held while they reconnect — say so, so a stalled
            // turn reads as "waiting for Bob" instead of "the game is broken".
            const isGone = disconnected.includes(player.uuid);
            return (
                <div
                    key={player.uuid || idx}
                    className={`player-chip${isCurrent ? ' is-current' : ''}${isMe ? ' is-me' : ''}${isGone ? ' is-disconnected' : ''}`}
                    title={isGone ? `${player.name} lost connection` : undefined}
                >
                    {player.name}
                    {isMe && ' (you)'}
                    {isGone && ' ⚠'}
                    {isCurrent && ' ◀'}
                </div>
            );
        })}
    </div>
);

export default PlayersBar;
