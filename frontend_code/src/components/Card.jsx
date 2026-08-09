import { SUIT_SYMBOLS, SUIT_COLORS, RANK_LABELS } from '../constants/cards';

const Card = ({ card, selected, onClick }) => {
    const isJoker = card.rank === 'JOKER';
    const suitSymbol = SUIT_SYMBOLS[card.suit] || card.suit;
    const rankLabel = RANK_LABELS[card.rank] ?? card.rank;
    const color = SUIT_COLORS[card.suit] || '#2c3e50';

    const className = `playing-card${selected ? ' is-selected' : ''}${onClick ? ' is-clickable' : ''}`;

    return (
        <div
            className={className}
            style={{ color }}
            onClick={onClick}
            title={`${rankLabel} ${suitSymbol}`}
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
