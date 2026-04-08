const SUIT_SYMBOLS = {
    'HEART': '\u2665',
    'DIAMOND': '\u2666',
    'CLUB': '\u2663',
    'SPADE': '\u2660',
    'SMALL': 'Jk',
    'BIG': 'JK',
};

const SUIT_COLORS = {
    'HEART': '#c0392b',
    'DIAMOND': '#c0392b',
    'CLUB': '#2c3e50',
    'SPADE': '#2c3e50',
    'SMALL': '#2c3e50',
    'BIG': '#c0392b',
};

const RANK_DISPLAY = {
    'ACE': 'A',
    'TWO': '2',
    'THREE': '3',
    'FOUR': '4',
    'FIVE': '5',
    'SIX': '6',
    'SEVEN': '7',
    'EIGHT': '8',
    'NINE': '9',
    'TEN': '10',
    'JACK': 'J',
    'QUEEN': 'Q',
    'KING': 'K',
    'JOKER': '',
};

const Card = ({ card, selected, onClick }) => {
    const suit = card.suit;
    const rank = card.rank;
    const isJoker = rank === 'JOKER';
    const suitSymbol = SUIT_SYMBOLS[suit] || suit;
    const rankDisplay = RANK_DISPLAY[rank] || rank;
    const color = SUIT_COLORS[suit] || '#2c3e50';

    const cardStyle = {
        display: 'inline-flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        width: '56px',
        height: '84px',
        border: selected ? '2px solid #3498db' : '1px solid #d5d8dc',
        borderRadius: '8px',
        backgroundColor: selected ? '#ebf5fb' : '#fff',
        color: color,
        fontSize: '14px',
        fontWeight: 'bold',
        cursor: onClick ? 'pointer' : 'default',
        margin: '2px',
        boxShadow: selected
            ? '0 0 8px rgba(52,152,219,0.5), 0 2px 4px rgba(0,0,0,0.1)'
            : '0 1px 3px rgba(0,0,0,0.12)',
        userSelect: 'none',
        transition: 'transform 0.1s, box-shadow 0.15s, border-color 0.15s',
        position: 'relative',
    };

    if (onClick) {
        cardStyle[':hover'] = { transform: 'translateY(-4px)' };
    }

    return (
        <div
            style={cardStyle}
            onClick={onClick}
            title={`${rankDisplay} ${suitSymbol}`}
            onMouseEnter={onClick ? (e) => { e.currentTarget.style.transform = 'translateY(-6px)'; } : undefined}
            onMouseLeave={onClick ? (e) => { e.currentTarget.style.transform = 'translateY(0)'; } : undefined}
        >
            {isJoker ? (
                <span style={{ fontSize: '18px' }}>{suitSymbol}</span>
            ) : (
                <>
                    <span style={{ fontSize: '15px', lineHeight: 1 }}>{rankDisplay}</span>
                    <span style={{ fontSize: '17px', lineHeight: 1, marginTop: '2px' }}>{suitSymbol}</span>
                </>
            )}
        </div>
    );
};

export default Card;
