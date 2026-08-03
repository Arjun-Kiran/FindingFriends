const PlayersBar = ({ players = [], currentPlayer, myUuid }) => (
    <div className="players-bar">
        {players.map((player, idx) => {
            const isCurrent = currentPlayer && currentPlayer.uuid === player.uuid;
            const isMe = player.uuid === myUuid;
            return (
                <div
                    key={player.uuid || idx}
                    className={`player-chip${isCurrent ? ' is-current' : ''}${isMe ? ' is-me' : ''}`}
                >
                    {player.name}
                    {isMe && ' (you)'}
                    {isCurrent && ' ◀'}
                </div>
            );
        })}
    </div>
);

export default PlayersBar;
