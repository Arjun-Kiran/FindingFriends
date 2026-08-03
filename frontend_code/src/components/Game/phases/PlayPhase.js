import { SOCKET_EVENTS } from '../../../api/events';

/** How many cards must be played this turn — null when leading (any number). */
const cardsToPlay = (view) => {
    const leadingHand = view.leading_hand_of_subround || [];
    return leadingHand.length === 0 ? null : leadingHand.length;
};

export const handRules = (view) => (view.my_turn ? { max: cardsToPlay(view) } : null);

const PlayPhase = ({ view, emit, selection }) => {
    const required = cardsToPlay(view);
    const isLeading = required === null;
    const hand = view.player_hand || [];

    if (!view.my_turn) {
        const waitingOn = (view.current_player && view.current_player.name) || '...';
        return (
            <div className="turn-indicator waiting-turn">
                Waiting for {waitingOn} to play...
            </div>
        );
    }

    const canPlay = selection.count > 0 && (isLeading || selection.count === required);

    const play = () => emit(SOCKET_EVENTS.PLAY_CARDS, {
        cards: selection.indices.map(idx => ({ suit: hand[idx].suit, rank: hand[idx].rank })),
    });

    return (
        <div>
            <div className="turn-indicator your-turn">
                {isLeading
                    ? `It's your turn to lead! Select 1 or more cards.`
                    : `It's your turn! Select ${required > 1 ? `${required} cards` : 'a card'} to play.`}
                {selection.count > 0 && (isLeading
                    ? ` (${selection.count} selected)`
                    : ` (${selection.count}/${required} selected)`)}
            </div>
            {canPlay && (
                <button className="btn btn-primary btn-inline" onClick={play}>
                    Play {selection.count} card{selection.count > 1 ? 's' : ''}
                </button>
            )}
        </div>
    );
};

export default PlayPhase;
