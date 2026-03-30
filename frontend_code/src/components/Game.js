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

const NON_TRUMP_SUITS = ['HEART', 'DIAMOND', 'CLUB', 'SPADE'];

const RANK_OPTIONS = [
    'ACE', 'KING', 'QUEEN', 'JACK', 'TEN',
    'NINE', 'EIGHT', 'SEVEN', 'SIX', 'FIVE',
    'FOUR', 'THREE', 'TWO',
];

const Game = ({ sessionInfo, initialGameState, socket }) => {
    const [gameState, setGameState] = useState(initialGameState || {});
    const [selectedCardIdx, setSelectedCardIdx] = useState(null);
    const [selectedCardIndices, setSelectedCardIndices] = useState(new Set());
    // Friend calling state: array of {suit, rank, order}
    const [callingCards, setCallingCards] = useState([]);
    const player_uuid = sessionInfo['user_uuid'];

    useEffect(() => {
        if (!socket) return;

        const handleGameStats = (data) => {
            console.log('Game received game_stats', data);
            setGameState(data);
            setSelectedCardIdx(null);
            setSelectedCardIndices(new Set());
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
    const numFriendsToCall = gameState.num_friends_to_call || 0;
    const friendCallingCards = gameState.friend_calling_cards || [];
    const leadingHand = gameState.leading_hand_of_subround || [];
    const revealedFriends = gameState.revealed_friends || [];
    const onAlphaTeam = gameState.on_alpha_team || false;
    const winningPlayer = gameState.winning_player_of_round;

    // --- Trump Declaration Logic ---
    const isTrumpPhase = phase === 'waiting-on-alpha-choose-trump';
    const canDeclareTrump = isTrumpPhase && isAlpha;

    const isEligibleTrumpCard = (card) => {
        if (!canDeclareTrump) return false;
        return card.rank === myLevel;
    };

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

    // --- Friend Calling Logic ---
    const isFriendPhase = phase === 'waiting-on-alpha-friend-card-choice';
    const canCallFriends = isFriendPhase && isAlpha;

    // Initialize calling cards slots when entering friend phase
    useEffect(() => {
        if (canCallFriends && callingCards.length !== numFriendsToCall) {
            setCallingCards(
                Array.from({ length: numFriendsToCall }, () => ({ suit: 'CLUB', rank: 'ACE', order: 1 }))
            );
        }
    }, [canCallFriends, numFriendsToCall, callingCards.length]);

    const updateCallingCard = (index, field, value) => {
        setCallingCards(prev => {
            const updated = [...prev];
            updated[index] = { ...updated[index], [field]: value };
            return updated;
        });
    };

    const handleCallFriends = () => {
        if (!socket) return;
        socket.emit('call_friends', {
            game_code: sessionInfo['game_code'],
            player_uuid: player_uuid,
            calling_cards: callingCards,
        });
    };

    // --- Kitty Exchange Logic ---
    const isKittyPhase = phase === 'waiting-on-alpha-kitty-sort';
    const canExchangeKitty = isKittyPhase && isAlpha;

    const toggleKittyCard = (idx) => {
        if (!canExchangeKitty) return;
        setSelectedCardIndices(prev => {
            const next = new Set(prev);
            if (next.has(idx)) {
                next.delete(idx);
            } else {
                // Only allow selecting up to kittySize cards
                // kittySize is 0 during kitty phase (cards are in hand now),
                // but we know the kitty was added, so use card_out_of_play count or calculate
                if (next.size < kittySize) {
                    next.add(idx);
                }
            }
            return next;
        });
    };

    const handleKittyExchange = () => {
        if (!socket) return;
        const discardedCards = Array.from(selectedCardIndices).map(idx => ({
            suit: hand[idx].suit,
            rank: hand[idx].rank,
        }));
        socket.emit('kitty_exchange', {
            game_code: sessionInfo['game_code'],
            player_uuid: player_uuid,
            discarded_cards: discardedCards,
        });
        setSelectedCardIndices(new Set());
    };

    // --- Card Play Logic ---
    const isPlayPhase = phase === 'round-started';

    const handlePlayCardClick = (idx) => {
        if (!isPlayPhase || !myTurn) return;
        setSelectedCardIdx(prev => prev === idx ? null : idx);
    };

    const handlePlayCard = () => {
        if (selectedCardIdx === null || !socket || !myTurn) return;
        const card = hand[selectedCardIdx];
        socket.emit('play_cards', {
            game_code: sessionInfo['game_code'],
            player_uuid: player_uuid,
            card: { suit: card.suit, rank: card.rank },
        });
        setSelectedCardIdx(null);
    };

    // Determine which suits are NOT trump (for friend calling validation display)
    const nonTrumpSuits = NON_TRUMP_SUITS.filter(s => s !== trumpSuit);
    const nonTrumpRanks = RANK_OPTIONS.filter(r => r !== trumpRank);

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
                    {Object.keys(eligibleSuits).length === 0 && (
                        <>
                            <p style={{ color: '#e74c3c', fontSize: '14px' }}>
                                You have no cards matching your level. Pick any suit:
                            </p>
                            <div style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
                                {NON_TRUMP_SUITS.map(suit => (
                                    <button key={suit} onClick={() => {
                                        if (!socket) return;
                                        socket.emit('declare_trump', {
                                            game_code: sessionInfo['game_code'],
                                            player_uuid: player_uuid,
                                            suit: suit,
                                            rank: myLevel,
                                        });
                                    }} style={{
                                        padding: '8px 16px', fontSize: '18px', cursor: 'pointer',
                                        borderRadius: '6px', border: '1px solid #bdc3c7', backgroundColor: '#fff',
                                    }}>
                                        {SUIT_SYMBOLS[suit]}
                                    </button>
                                ))}
                            </div>
                        </>
                    )}
                    {selectedCardIdx !== null && (
                        <button onClick={handleDeclareTrump} style={{
                            padding: '8px 20px', fontSize: '15px', cursor: 'pointer',
                            borderRadius: '6px', backgroundColor: '#e67e22', color: '#fff',
                            border: 'none', marginTop: '8px',
                        }}>
                            Declare {SUIT_SYMBOLS[hand[selectedCardIdx]?.suit] || ''} as Trump
                        </button>
                    )}
                </div>
            )}

            {/* Friend Calling UI */}
            {isFriendPhase && !isAlpha && (
                <div style={{ marginBottom: '10px', padding: '10px', backgroundColor: '#fef9e7', borderRadius: '6px' }}>
                    Trump: <strong>{SUIT_SYMBOLS[trumpSuit] || trumpSuit} {trumpRank}</strong>. Waiting for alpha to call friends...
                </div>
            )}
            {canCallFriends && (
                <div style={{ marginBottom: '15px', padding: '15px', backgroundColor: '#eaf2f8', borderRadius: '8px' }}>
                    <strong>Call {numFriendsToCall} Friend Card{numFriendsToCall > 1 ? 's' : ''}</strong>
                    <p style={{ margin: '8px 0', fontSize: '14px' }}>
                        Specify which cards will reveal your secret partners. Called cards must not be trumps.
                    </p>
                    {callingCards.map((cc, idx) => (
                        <div key={idx} style={{ display: 'flex', gap: '8px', alignItems: 'center', marginBottom: '8px' }}>
                            <span style={{ fontWeight: 'bold', minWidth: '20px' }}>#{idx + 1}</span>
                            <select value={cc.order} onChange={e => updateCallingCard(idx, 'order', parseInt(e.target.value))}
                                style={{ padding: '4px 8px' }}>
                                <option value={1}>1st</option>
                                <option value={2}>2nd</option>
                                <option value={3}>3rd</option>
                                <option value={4}>4th</option>
                            </select>
                            <select value={cc.rank} onChange={e => updateCallingCard(idx, 'rank', e.target.value)}
                                style={{ padding: '4px 8px' }}>
                                {nonTrumpRanks.map(r => (
                                    <option key={r} value={r}>{r}</option>
                                ))}
                            </select>
                            <span>of</span>
                            <select value={cc.suit} onChange={e => updateCallingCard(idx, 'suit', e.target.value)}
                                style={{ padding: '4px 8px' }}>
                                {nonTrumpSuits.map(s => (
                                    <option key={s} value={s}>{SUIT_SYMBOLS[s]} {s}</option>
                                ))}
                            </select>
                        </div>
                    ))}
                    <button onClick={handleCallFriends} style={{
                        padding: '8px 20px', fontSize: '15px', cursor: 'pointer',
                        borderRadius: '6px', backgroundColor: '#2980b9', color: '#fff',
                        border: 'none', marginTop: '8px',
                    }}>
                        Confirm Friend Cards
                    </button>
                </div>
            )}

            {/* Called cards display (visible to everyone after calling) */}
            {friendCallingCards.length > 0 && phase !== 'waiting-on-alpha-friend-card-choice' && (
                <div style={{ marginBottom: '10px', padding: '10px', backgroundColor: '#f5f5f5', borderRadius: '6px', fontSize: '13px' }}>
                    <strong>Called Cards:</strong>{' '}
                    {friendCallingCards.map((cc, idx) => (
                        <span key={idx}>
                            {idx > 0 && ', '}
                            {cc.order === 1 ? '1st' : cc.order === 2 ? '2nd' : cc.order === 3 ? '3rd' : `${cc.order}th`}{' '}
                            {cc.rank} of {SUIT_SYMBOLS[cc.suit] || cc.suit}
                        </span>
                    ))}
                </div>
            )}

            {/* Kitty Exchange UI */}
            {isKittyPhase && !isAlpha && (
                <div style={{ marginBottom: '10px', padding: '10px', backgroundColor: '#fef9e7', borderRadius: '6px' }}>
                    Waiting for alpha to exchange kitty cards...
                </div>
            )}
            {canExchangeKitty && (
                <div style={{ marginBottom: '15px', padding: '15px', backgroundColor: '#fdf2e9', borderRadius: '8px' }}>
                    <strong>Kitty Exchange</strong>
                    <p style={{ margin: '8px 0', fontSize: '14px' }}>
                        The kitty ({kittySize} cards) has been added to your hand. Select {kittySize} cards to discard face-down.
                    </p>
                    <p style={{ fontSize: '13px', color: '#7f8c8d' }}>
                        Selected: {selectedCardIndices.size} / {kittySize}
                    </p>
                    {selectedCardIndices.size === kittySize && (
                        <button onClick={handleKittyExchange} style={{
                            padding: '8px 20px', fontSize: '15px', cursor: 'pointer',
                            borderRadius: '6px', backgroundColor: '#27ae60', color: '#fff',
                            border: 'none', marginTop: '4px',
                        }}>
                            Confirm Discard
                        </button>
                    )}
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

            {/* Turn indicator + Play button */}
            {phase === 'round-started' && (
                <div style={{ marginBottom: '10px' }}>
                    <div style={{ fontSize: '14px', fontWeight: 'bold', marginBottom: '6px' }}>
                        {myTurn
                            ? <span style={{ color: '#27ae60' }}>It's your turn! Select a card to play.</span>
                            : <span style={{ color: '#7f8c8d' }}>Waiting for {currentPlayer?.name || '...'} to play...</span>
                        }
                    </div>
                    {myTurn && selectedCardIdx !== null && (
                        <button onClick={handlePlayCard} style={{
                            padding: '8px 20px', fontSize: '15px', cursor: 'pointer',
                            borderRadius: '6px', backgroundColor: '#27ae60', color: '#fff',
                            border: 'none',
                        }}>
                            Play {hand[selectedCardIdx]?.rank} of {SUIT_SYMBOLS[hand[selectedCardIdx]?.suit] || hand[selectedCardIdx]?.suit}
                        </button>
                    )}
                </div>
            )}

            {/* Revealed friends */}
            {revealedFriends.length > 0 && (
                <div style={{ marginBottom: '10px', padding: '8px', backgroundColor: '#e8f8f5', borderRadius: '6px', fontSize: '13px' }}>
                    <strong>Revealed Friends:</strong>{' '}
                    {revealedFriends.map((uuid, idx) => {
                        const p = playerList.find(pl => pl.uuid === uuid);
                        return <span key={uuid}>{idx > 0 && ', '}{p?.name || uuid}</span>;
                    })}
                </div>
            )}

            {/* Round ended summary */}
            {phase === 'round-ended' && (
                <div style={{ marginBottom: '15px', padding: '15px', backgroundColor: '#fef9e7', borderRadius: '8px' }}>
                    <h3 style={{ margin: '0 0 10px 0' }}>Round Over!</h3>
                    <p style={{ fontSize: '14px' }}>
                        {onAlphaTeam
                            ? 'You were on the Alpha team.'
                            : 'You were on the Defender team.'}
                    </p>
                    <h4 style={{ margin: '8px 0 4px 0' }}>Scores</h4>
                    <div style={{ fontSize: '13px' }}>
                        {playerList.map(player => (
                            <div key={player.uuid}>
                                {player.name}: {gameState.players_round_score?.[player.uuid] || 0} pts
                            </div>
                        ))}
                    </div>
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
                        const selected = selectedCardIdx === idx || selectedCardIndices.has(idx);
                        const dimmed = canDeclareTrump && !eligible;

                        let onClick;
                        if (canDeclareTrump && eligible) {
                            onClick = () => handleCardClick(idx);
                        } else if (canExchangeKitty) {
                            onClick = () => toggleKittyCard(idx);
                        } else if (isPlayPhase && myTurn) {
                            onClick = () => handlePlayCardClick(idx);
                        }

                        return (
                            <div key={idx} style={{ opacity: dimmed ? 0.4 : 1 }}>
                                <Card card={card} selected={selected} onClick={onClick} />
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}

export default Game;
