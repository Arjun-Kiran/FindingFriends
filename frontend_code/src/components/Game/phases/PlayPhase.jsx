import { SOCKET_EVENTS } from '../../../api/events';
import { Avatar, Icon } from '../../Emoji';
import { STATUS_EMOJI } from '../../../constants/emoji';

/** How many cards must be played this turn — null when leading (any number). */
const cardsToPlay = (view) => {
    const leadingHand = view.leading_hand_of_subround || [];
    return leadingHand.length === 0 ? null : leadingHand.length;
};

export const handRules = (view) => (view.my_turn ? { max: cardsToPlay(view) } : null);

/** Have enough cards been picked to make a legal-sized play? */
const readyToPlay = (view, selection) => {
    const required = cardsToPlay(view);
    return selection.count > 0 && (required === null || selection.count === required);
};

/* What to say when the highlight has nothing to narrow down — every card in
 * hand could legally be part of this play.
 *
 * "Any card" on its own is half an answer: against a pair you may play any two
 * cards, and a player who reads "any card" and picks one gets refused. So the
 * count comes with it. Written here rather than in the hand, because how many
 * cards a play needs is this phase's business. */
export const handNote = (view) => {
    const required = cardsToPlay(view);
    if (required === null) return 'Nothing has been led — any card, or any legal set, can go.';
    return required === 1
        ? 'Nothing is ruled out — any single card in your hand can be played.'
        : `Nothing is ruled out — any ${required} of your cards can be played.`;
};

/* The confirm button, drawn in the hand area rather than in the panel above.
 *
 * It acts on the cards, so it belongs beside them: picking cards and confirming
 * them were a reach apart with the button up here. The panel keeps the turn
 * indicator, which is a thing you read rather than a thing you press. */
export const handAction = ({ view, emit, selection }) => {
    if (!view.my_turn || !readyToPlay(view, selection)) return null;

    const hand = view.player_hand || [];
    const play = () => emit(SOCKET_EVENTS.PLAY_CARDS, {
        cards: selection.indices.map(idx => ({ suit: hand[idx].suit, rank: hand[idx].rank })),
    });

    return (
        <button className="btn btn-primary btn-inline" onClick={play}>
            Play {selection.count} card{selection.count > 1 ? 's' : ''}
        </button>
    );
};

const PlayPhase = ({ view, selection }) => {
    const required = cardsToPlay(view);
    const isLeading = required === null;

    if (!view.my_turn) {
        const current = view.current_player;
        const waitingOn = (current && current.name) || '...';
        // Without this the table just stops, with no way to tell a slow player
        // from one whose connection dropped.
        const isGone = current && (view.disconnected_players || []).includes(current.uuid);
        return (
            <div className="turn-indicator waiting-turn">
                {current && <Avatar player={current} />}{' '}
                {isGone ? (
                    <>
                        <Icon emoji={STATUS_EMOJI.DISCONNECTED} label="Lost connection" />
                        {`${waitingOn} lost connection — waiting for them to rejoin...`}
                    </>
                ) : `Waiting for ${waitingOn} to play...`}
            </div>
        );
    }

    return (
        <div>
            <div className="turn-indicator your-turn">
                <Icon emoji={STATUS_EMOJI.CURRENT_TURN} label="Your turn" />
                {isLeading
                    ? `It's your turn to lead! Select 1 or more cards.`
                    : `It's your turn! Select ${required > 1 ? `${required} cards` : 'a card'} to play.`}
                {selection.count > 0 && (isLeading
                    ? ` (${selection.count} selected)`
                    : ` (${selection.count}/${required} selected)`)}
            </div>
        </div>
    );
};

export default PlayPhase;
