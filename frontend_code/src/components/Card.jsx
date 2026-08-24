import { SUIT_SYMBOLS, SUIT_COLORS, RANK_LABELS, JOKER_LABELS } from '../constants/cards';

const Card = ({ card, selected, onClick }) => {
    const isJoker = card.rank === 'JOKER';
    const suitSymbol = SUIT_SYMBOLS[card.suit] || card.suit;
    const rankLabel = RANK_LABELS[card.rank] ?? card.rank;
    const color = SUIT_COLORS[card.suit] || '#2c3e50';

    const className = `playing-card${selected ? ' is-selected' : ''}${onClick ? ' is-clickable' : ''}`;

    // A joker has no rank label, so "${rank} ${suit}" would read as " JK🤡".
    const title = isJoker
        ? (JOKER_LABELS[card.suit] || 'Joker')
        : `${rankLabel} ${suitSymbol}`;

    return (
        <div
            className={className}
            style={{ color }}
            onClick={onClick}
            title={title}
        >
            {isJoker ? (
                <span className="playing-card-joker">{suitSymbol}</span>
            ) : (
                <>
                    <span className="playing-card-rank">{rankLabel}</span>
                    <span className="playing-card-suit">{suitSymbol}</span>
                </>
            )}
        </div>
    );
};

export default Card;
