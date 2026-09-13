import { SOCKET_EVENTS } from '../../../api/events';
import { Avatar, Icon } from '../../Emoji';
import { STATUS_EMOJI } from '../../../constants/emoji';

/** How many cards must be played this turn — null when leading (any number). */
const cardsToPlay = (view) => {
    const leadingHand = view.leading_hand_of_subround || [];
    return leadingHand.length === 0 ? null : leadingHand.length;
};

/** Are this player's cards already in the trick on the table? */
const playedThisTrick = (view) => (view.active_pile_player_uuids || []).includes(view.uuid);

/** Could this player pick their answer now, ahead of their turn? Only once
 * there is a lead to answer and they have not answered it — before the lead
 * there is no question yet, and after their play the next one is unknown. */
const canPickAhead = (view) => !view.my_turn && cardsToPlay(view) !== null && !playedThisTrick(view);

export const handRules = (view) => (
    view.my_turn || canPickAhead(view) ? { max: cardsToPlay(view) } : null
);

/** Have enough cards been picked to make a legal-sized play? */
const readyToPlay = (view, selection) => {
    const required = cardsToPlay(view);
    return selection.count > 0 && (required === null || selection.count === required);
};

const cardCount = (count) => `${count} card${count > 1 ? 's' : ''}`;

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
 * indicator, which is a thing you read rather than a thing you press.
 *
 * Off your turn the same spot offers to queue a pick the server has called
 * legal, and to take the queue back. */
export const handAction = ({ view, emit, selection, preselect }) => {
    // A queued play stays cancellable through the pause after the turn arrives,
    // and offering Play beside it then would invite playing the cards twice.
    if (preselect && preselect.queued) {
        return (
            <button className="btn btn-primary btn-inline" onClick={preselect.cancel}>
                Cancel auto-play
            </button>
        );
    }

    if (view.my_turn) {
        if (!readyToPlay(view, selection)) return null;

        const hand = view.player_hand || [];
        const play = () => emit(SOCKET_EVENTS.PLAY_CARDS, {
            cards: selection.indices.map(idx => ({ suit: hand[idx].suit, rank: hand[idx].rank })),
        });

        return (
            <button className="btn btn-primary btn-inline" onClick={play}>
                Play {cardCount(selection.count)}
            </button>
        );
    }

    if (preselect && preselect.canQueue) {
        return (
            <button className="btn btn-primary btn-inline" onClick={preselect.queue}>
                Auto-play {cardCount(selection.count)} on my turn
            </button>
        );
    }
    return null;
};

/* The server's verdict on the cards picked to answer the trick, in words. Shown
 * on your turn as well as before it: finding out a play is illegal before
 * pressing the button beats finding out after. */
export const handStatus = ({ view, preselect }) => {
    if (!preselect || preselect.status === 'idle') return null;

    const line = (tone, emoji, label, text) => (
        <p className={`hand-status is-${tone}`} role="status">
            {emoji && <Icon emoji={emoji} label={label} />}
            {text}
        </p>
    );

    if (preselect.status === 'checking') {
        return line('checking', null, '', 'Checking those cards…');
    }
    if (preselect.status === 'illegal') {
        return line('illegal', STATUS_EMOJI.PLAY_ILLEGAL, 'Not legal', `Not a legal play: ${preselect.message}`);
    }
    if (preselect.queued) {
        return line('queued', STATUS_EMOJI.PLAY_QUEUED, 'Queued', view.my_turn
            ? 'Your turn — playing your queued cards in a moment.'
            : 'Queued — these will be played when it is your turn. Change a card to take them back.');
    }
    return line('legal', STATUS_EMOJI.PLAY_LEGAL, 'Legal', view.my_turn
        ? 'Legal play.'
        : 'Legal play — auto-play it and it goes the moment your turn comes.');
};

const PlayPhase = ({ view, selection, preselect }) => {
    const required = cardsToPlay(view);
    const isLeading = required === null;

    if (!view.my_turn) {
        const current = view.current_player;
        const waitingOn = (current && current.name) || '...';
        // Without this the table just stops, with no way to tell a slow player
        // from one whose connection dropped.
        const isGone = current && (view.disconnected_players || []).includes(current.uuid);
        let aside = '';
        if (preselect && preselect.queued) {
            aside = 'Your cards are queued to play.';
        } else if (canPickAhead(view)) {
            aside = `You can pick your ${required > 1 ? `${required} cards` : 'card'} now.`;
        }
        return (
            <div className="turn-indicator waiting-turn">
                {current && <Avatar player={current} />}{' '}
                {isGone ? (
                    <>
                        <Icon emoji={STATUS_EMOJI.DISCONNECTED} label="Lost connection" />
                        {`${waitingOn} lost connection — waiting for them to rejoin...`}
                    </>
                ) : `Waiting for ${waitingOn} to play...`}
                {aside && <span className="turn-indicator-aside"> {aside}</span>}
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
