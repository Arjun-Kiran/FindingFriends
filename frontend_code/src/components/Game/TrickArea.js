import Card from '../Card';

const TrickArea = ({ cards = [] }) => {
    if (cards.length === 0) return null;

    return (
        <div className="trick-area">
            <h4>Current Trick</h4>
            <div className="trick-cards">
                {cards.map((card, idx) => <Card key={idx} card={card} selected={false} />)}
            </div>
        </div>
    );
};

export default TrickArea;
