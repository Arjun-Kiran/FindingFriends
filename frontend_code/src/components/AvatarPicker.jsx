/* Pick the animal that stands for you at the table.
 *
 * Everyone already has one — the server assigns one on the way in — so this
 * changes a choice rather than making a first one, and there is no "unpicked"
 * state to design around.
 *
 * Avatars other players hold are shown disabled rather than hidden: dropping
 * them from the grid would reshuffle every remaining animal under the player's
 * finger each time someone else picked.
 */
const AvatarPicker = ({ choices = [], taken = [], mine = '', onChoose, disabled = false }) => {
    if (choices.length === 0) return null;

    const takenByOthers = new Set(taken.filter(avatar => avatar !== mine));

    return (
        <div className="avatar-picker">
            <h3 className="avatar-picker-heading">Your animal</h3>
            <div className="avatar-grid" role="group" aria-label="Choose your avatar">
                {choices.map(choice => {
                    const isMine = choice === mine;
                    const isTaken = takenByOthers.has(choice);
                    return (
                        <button
                            key={choice}
                            type="button"
                            className={`avatar-option${isMine ? ' is-mine' : ''}${isTaken ? ' is-taken' : ''}`}
                            onClick={() => onChoose(choice)}
                            disabled={disabled || isTaken || isMine}
                            aria-pressed={isMine}
                            title={isTaken ? 'Taken by another player' : undefined}
                        >
                            {choice}
                        </button>
                    );
                })}
            </div>
        </div>
    );
};

export default AvatarPicker;
