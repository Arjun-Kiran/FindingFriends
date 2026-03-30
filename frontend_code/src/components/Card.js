const SUIT_SYMBOLS = {
    'HEART': '\u2665',
    'DIAMOND': '\u2666',
    'CLUB': '\u2663',
    'SPADE': '\u2660',
    'SMALL': 'Jk',
    'BIG': 'JK',
};

const SUIT_COLORS = {
    'HEART': '#e74c3c',
    'DIAMOND': '#e74c3c',
    'CLUB': '#2c3e50',
    'SPADE': '#2c3e50',
    'SMALL': '#2c3e50',
    'BIG': '#e74c3c',
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
        width: '60px',
        height: '90px',
        border: selected ? '3px solid #3498db' : '1px solid #bdc3c7',
        borderRadius: '8px',
        backgroundColor: selected ? '#ebf5fb' : '#fff',
        color: color,
        fontSize: '14px',
        fontWeight: 'bold',
        cursor: onClick ? 'pointer' : 'default',
        margin: '2px',
        boxShadow: selected ? '0 0 6px rgba(52,152,219,0.5)' : '0 1px 3px rgba(0,0,0,0.15)',
        userSelect: 'none',
        transition: 'transform 0.1s, box-shadow 0.1s',
    };

    return (
        <div style={cardStyle} onClick={onClick} title={`${rankDisplay} ${suitSymbol}`}>
            {isJoker ? (
                <span style={{ fontSize: '20px' }}>{suitSymbol}</span>
            ) : (
                <>
                    <span style={{ fontSize: '16px' }}>{rankDisplay}</span>
                    <span style={{ fontSize: '18px' }}>{suitSymbol}</span>
                </>
            )}
        </div>
    );
};

export default Card;
