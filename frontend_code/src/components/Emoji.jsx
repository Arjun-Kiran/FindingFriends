import { DEFAULT_AVATAR } from '../constants/emoji';

/* A player's animal avatar.
 *
 * This one is the player's identity rather than decoration, so it is announced
 * rather than hidden. Falls back for players from games saved before avatars
 * existed. */
export const Avatar = ({ player, className = '' }) => {
    const glyph = (player && player.avatar) || DEFAULT_AVATAR;
    const name = (player && player.name) || 'Player';
    return (
        <span
            className={`avatar${className ? ` ${className}` : ''}`}
            role="img"
            aria-label={`${name}'s avatar`}
        >
            {glyph}
        </span>
    );
};

/* A decorative icon sitting beside a text label that already says the same
 * thing, so it is hidden from screen readers and carries a tooltip for anyone
 * unsure what it means. */
export const Icon = ({ emoji, label }) => (
    <span className="ui-icon" aria-hidden="true" title={label}>{emoji}</span>
);
