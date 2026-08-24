import { Avatar, Icon } from '../Emoji';
import { ROLE_EMOJI, STATUS_EMOJI } from '../../constants/emoji';

const PlayersBar = ({
    players = [],
    currentPlayer,
    myUuid,
    disconnected = [],
    alphaUuid = '',
    revealedFriends = [],
}) => (
    <div className="players-bar">
        {players.map((player, idx) => {
            const isCurrent = currentPlayer && currentPlayer.uuid === player.uuid;
            const isMe = player.uuid === myUuid;
            const isAlpha = alphaUuid && player.uuid === alphaUuid;
            // Only friends who have revealed themselves by playing a called
            // card — the rest of the table is still a secret.
            const isFriend = revealedFriends.includes(player.uuid);
            // Their seat is held while they reconnect — say so, so a stalled
            // turn reads as "waiting for Bob" instead of "the game is broken".
            const isGone = disconnected.includes(player.uuid);
            return (
                <div
                    key={player.uuid || idx}
                    className={`player-chip${isCurrent ? ' is-current' : ''}${isMe ? ' is-me' : ''}${isGone ? ' is-disconnected' : ''}`}
                    title={isGone ? `${player.name} lost connection` : undefined}
                >
                    <Avatar player={player} />
                    <span className="player-chip-name">{player.name}</span>
                    {isMe && <Icon emoji={ROLE_EMOJI.YOU} label="You" />}
                    {isAlpha && <Icon emoji={ROLE_EMOJI.ALPHA} label="Alpha player" />}
                    {isFriend && <Icon emoji={ROLE_EMOJI.FRIEND} label="Revealed friend" />}
                    {isGone && <Icon emoji={STATUS_EMOJI.DISCONNECTED} label="Lost connection" />}
                    {isCurrent && <Icon emoji={STATUS_EMOJI.CURRENT_TURN} label="Their turn" />}
                </div>
            );
        })}
    </div>
);

export default PlayersBar;
