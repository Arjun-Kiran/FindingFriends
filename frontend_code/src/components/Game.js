import { useEffect, useState } from "react";
import Card from "./Card";

const PHASE_LABELS = {
    'waiting-on-alpha-choose-trump': 'Trump Declaration',
    'waiting-on-alpha-friend-card-choice': 'Friend Calling',
    'waiting-on-alpha-kitty-sort': 'Kitty Exchange',
    'round-started': 'Round in Progress',
    'round-ended': 'Round Ended',
    'game-ended': 'Game Over',
};

const SUIT_SYMBOLS = {
    'HEART': '\u2665',
    'DIAMOND': '\u2666',
    'CLUB': '\u2663',
    'SPADE': '\u2660',
};

const Game = ({ sessionInfo, initialGameState, socket }) => {
    const [gameState, setGameState] = useState(initialGameState || {});
    const [selectedCardIdx, setSelectedCardIdx] = useState(null);
    const player_uuid = sessionInfo['user_uuid'];

    useEffect(() => {
        if (!socket) return;

        const handleGameStats = (data) => {
            console.log('Game received game_stats', data);
            setGameState(data);
            setSelectedCardIdx(null);
        };

        socket.on('game_stats', handleGameStats);

        return () => {
            socket.off('game_stats', handleGameStats);
        };
    }, [socket]);

    const phase = gameState.game_event_state || '';
    const phaseLabel = PHASE_LABELS[phase] || phase;
    const playerList = gameState.player_list || [];
    const hand = gameState.player_hand || [];
    const activePile = gameState.cards_in_active_pile || [];
    const isAlpha = gameState.is_alpha || false;
    const myTurn = gameState.my_turn || false;
    const currentPlayer = gameState.current_player;
    const trumpSuit = gameState.declare_trump?.suit;
    const trumpRank = gameState.declare_trump?.rank;
    const kittySize = gameState.kitty_size || 0;
    const myLevel = gameState.my_level || '';

    // During trump declaration, alpha can only select cards matching their level
    const isTrumpPhase = phase === 'waiting-on-alpha-choose-trump';
    const canDeclareTrump = isTrumpPhase && isAlpha;

    const isEligibleTrumpCard = (card) => {
        if (!canDeclareTrump) return false;
        return card.rank === myLevel;
    };

    // Count eligible trump cards by suit to help the alpha decide
    const eligibleSuits = {};
    if (canDeclareTrump) {
        hand.forEach(card => {
            if (card.rank === myLevel && card.suit !== 'SMALL' && card.suit !== 'BIG') {
                eligibleSuits[card.suit] = (eligibleSuits[card.suit] || 0) + 1;
            }
        });
    }

    const handleCardClick = (idx) => {
        if (canDeclareTrump && isEligibleTrumpCard(hand[idx])) {
            setSelectedCardIdx(idx);
        }
    };

    const handleDeclareTrump = () => {
        if (selectedCardIdx === null || !socket) return;
        const card = hand[selectedCardIdx];
        socket.emit('declare_trump', {
            game_code: sessionInfo['game_code'],
            player_uuid: player_uuid,
            suit: card.suit,
            rank: card.rank,
        });
        setSelectedCardIdx(null);
    };

    return (
        <div style={{ padding: '20px', maxWidth: '900px', margin: '0 auto' }}>
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '2px solid #ecf0f1', paddingBottom: '10px', marginBottom: '15px' }}>
                <div>
                    <h2 style={{ margin: 0 }}>Finding Friends</h2>
                    <span style={{ color: '#7f8c8d', fontSize: '14px' }}>Game: {sessionInfo['game_code']}</span>
                </div>
                <div style={{ textAlign: 'right' }}>
                    <div style={{ fontWeight: 'bold', color: '#2c3e50' }}>{phaseLabel}</div>
                    {trumpSuit && <div style={{ fontSize: '13px' }}>Trump: {trumpRank} of {SUIT_SYMBOLS[trumpSuit] || trumpSuit}</div>}
                    {isAlpha && <div style={{ fontSize: '13px', color: '#e67e22' }}>You are the Alpha</div>}
                    {kittySize > 0 && isTrumpPhase && (
                        <div style={{ fontSize: '13px', color: '#7f8c8d' }}>Kitty: {kittySize} cards</div>
                    )}
                </div>
            </div>

            {/* Players */}
            <div style={{ marginBottom: '15px' }}>
                <h4 style={{ margin: '0 0 8px 0' }}>Players</h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {playerList.map((player, idx) => {
                        const isCurrent = currentPlayer && currentPlayer.uuid === player.uuid;
                        const isMe = player.uuid === player_uuid;
                        return (
                            <div key={player.uuid || idx} style={{
                                padding: '6px 12px',
                                borderRadius: '6px',
                                border: isCurrent ? '2px solid #e67e22' : '1px solid #bdc3c7',
                                backgroundColor: isMe ? '#eaf2f8' : '#fff',
                                fontSize: '13px',
                            }}>
                                {player.name}
                                {isMe && ' (you)'}
                                {isCurrent && ' \u25C0'}
                            </div>
                        );
                    })}
                </div>
            </div>

            {/* Trump declaration UI */}
            {isTrumpPhase && !isAlpha && (
                <div style={{ marginBottom: '10px', padding: '10px', backgroundColor: '#fef9e7', borderRadius: '6px' }}>
                    Waiting for the alpha player to declare trump...
                </div>
            )}
            {canDeclareTrump && (
                <div style={{ marginBottom: '15px', padding: '15px', backgroundColor: '#fdf2e9', borderRadius: '8px' }}>
                    <strong>Declare Trump Suit</strong>
                    <p style={{ margin: '8px 0', fontSize: '14px' }}>
                        Your level is <strong>{myLevel}</strong>. Click a matching card below to select a trump suit, then confirm.
                    </p>
                    {Object.keys(eligibleSuits).length === 0 ? (
                        <p style={{ color: '#e74c3c', fontSize: '14px' }}>
                            You have no cards matching your level. You may pick any suit:
                        </p>
                    ) : null}
                    {Object.keys(eligibleSuits).length === 0 && (
                        <div style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
                            {['HEART', 'DIAMOND', 'CLUB', 'SPADE'].map(suit => (
                                <button key={suit} onClick={() => {
                                    if (!socket) return;
                                    socket.emit('declare_trump', {
                                        game_code: sessionInfo['game_code'],
                                        player_uuid: player_uuid,
                                        suit: suit,
                                        rank: myLevel,
                                    });
                                }} style={{
                                    padding: '8px 16px',
                                    fontSize: '18px',
                                    cursor: 'pointer',
                                    borderRadius: '6px',
                                    border: '1px solid #bdc3c7',
                                    backgroundColor: '#fff',
                                }}>
                                    {SUIT_SYMBOLS[suit]}
                                </button>
                            ))}
                        </div>
                    )}
                    {selectedCardIdx !== null && (
                        <button onClick={handleDeclareTrump} style={{
                            padding: '8px 20px',
                            fontSize: '15px',
                            cursor: 'pointer',
                            borderRadius: '6px',
                            backgroundColor: '#e67e22',
                            color: '#fff',
                            border: 'none',
                            marginTop: '8px',
                        }}>
                            Declare {SUIT_SYMBOLS[hand[selectedCardIdx]?.suit] || ''} as Trump
                        </button>
                    )}
                </div>
            )}

            {/* Friend calling placeholder */}
            {phase === 'waiting-on-alpha-friend-card-choice' && !isAlpha && (
                <div style={{ marginBottom: '10px', padding: '10px', backgroundColor: '#fef9e7', borderRadius: '6px' }}>
                    Trump declared: <strong>{SUIT_SYMBOLS[trumpSuit] || trumpSuit} {trumpRank}</strong>. Waiting for alpha to call friends...
                </div>
            )}
            {phase === 'waiting-on-alpha-friend-card-choice' && isAlpha && (
                <div style={{ marginBottom: '10px', padding: '10px', backgroundColor: '#fdf2e9', borderRadius: '6px' }}>
                    Trump declared: <strong>{SUIT_SYMBOLS[trumpSuit] || trumpSuit} {trumpRank}</strong>. Friend calling UI coming in Phase 3.
                </div>
            )}

            {/* Trick area */}
            {activePile.length > 0 && (
                <div style={{ marginBottom: '15px', padding: '15px', backgroundColor: '#f0f3f4', borderRadius: '8px' }}>
                    <h4 style={{ margin: '0 0 8px 0' }}>Current Trick</h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap' }}>
                        {activePile.map((card, idx) => (
                            <Card key={idx} card={card} selected={false} />
                        ))}
                    </div>
                </div>
            )}

            {/* Turn indicator */}
            {phase === 'round-started' && (
                <div style={{ marginBottom: '10px', fontSize: '14px', fontWeight: 'bold' }}>
                    {myTurn
                        ? <span style={{ color: '#27ae60' }}>It's your turn! Select a card to play.</span>
                        : <span style={{ color: '#7f8c8d' }}>Waiting for {currentPlayer?.name || '...'} to play...</span>
                    }
                </div>
            )}

            {/* Scores */}
            {gameState.players_round_score && Object.keys(gameState.players_round_score).length > 0 && (
                <div style={{ marginBottom: '15px' }}>
                    <h4 style={{ margin: '0 0 8px 0' }}>Round Scores</h4>
                    <div style={{ display: 'flex', gap: '12px', fontSize: '13px' }}>
                        {playerList.map((player) => (
                            <span key={player.uuid}>
                                {player.name}: {gameState.players_round_score[player.uuid] || 0}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Hand */}
            <div style={{ borderTop: '2px solid #ecf0f1', paddingTop: '15px' }}>
                <h4 style={{ margin: '0 0 8px 0' }}>Your Hand ({hand.length} cards)</h4>
                <div style={{ display: 'flex', flexWrap: 'wrap' }}>
                    {hand.map((card, idx) => {
                        const eligible = isEligibleTrumpCard(card);
                        const selected = selectedCardIdx === idx;
                        const dimmed = canDeclareTrump && !eligible;
                        return (
                            <div key={idx} style={{ opacity: dimmed ? 0.4 : 1 }}>
                                <Card
                                    card={card}
                                    selected={selected}
                                    onClick={eligible ? () => handleCardClick(idx) : undefined}
                                />
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}

export default Game;
