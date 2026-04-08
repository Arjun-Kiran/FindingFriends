import { useEffect, useState, useRef } from "react";
import { io } from "socket.io-client";
import Card from "./Card";

const PHASE_LABELS = {
    'waiting-on-alpha-choose-trump': 'Trump Declaration',
    'waiting-on-alpha-friend-card-choice': 'Friend Calling',
    'waiting-on-alpha-kitty-sort': 'Kitty Exchange',
    'round-started': 'Round in Progress',
    'round-ended': 'Round Ended',
    'game-ended': 'Game Over',
};

const PHASE_CLASSES = {
    'waiting-on-alpha-choose-trump': 'trump',
    'waiting-on-alpha-friend-card-choice': 'friend',
    'waiting-on-alpha-kitty-sort': 'kitty',
    'round-started': 'playing',
    'round-ended': 'ended',
    'game-ended': 'ended',
};

const SUIT_SYMBOLS = {
    'HEART': '\u2665',
    'DIAMOND': '\u2666',
    'CLUB': '\u2663',
    'SPADE': '\u2660',
};

const NON_TRUMP_SUITS = ['HEART', 'DIAMOND', 'CLUB', 'SPADE'];

const RANK_DISPLAY = {
    1: '2', 2: '3', 3: '4', 4: '5', 5: '6', 6: '7', 7: '8',
    8: '9', 9: '10', 10: 'J', 11: 'Q', 12: 'K', 13: 'A',
};

const RANK_OPTIONS = [
    'ACE', 'KING', 'QUEEN', 'JACK', 'TEN',
    'NINE', 'EIGHT', 'SEVEN', 'SIX', 'FIVE',
    'FOUR', 'THREE', 'TWO',
];

const Game = ({ sessionInfo, initialGameState, socket: externalSocket, onLeaveGame }) => {
    const [gameState, setGameState] = useState(initialGameState || {});
    const [selectedCardIdx, setSelectedCardIdx] = useState(null);
    const [selectedCardIndices, setSelectedCardIndices] = useState(new Set());
    const [errorMessage, setErrorMessage] = useState('');
    const [callingCards, setCallingCards] = useState([]);
    const player_uuid = sessionInfo['user_uuid'];
    const game_code = sessionInfo['game_code'];
    const ownSocketRef = useRef(null);

    const socket = externalSocket || ownSocketRef.current;

    useEffect(() => {
        if (externalSocket) return;
        const newSocket = io("http://127.0.0.1:5050", { transports: ["websocket"] });
        ownSocketRef.current = newSocket;
        newSocket.on("connect", () => {
            console.log("Game reconnected to websocket");
            newSocket.emit('join', { game_code, player_uuid });
        });
        newSocket.on("disconnect", () => console.log("Game disconnected from websocket"));
        return () => newSocket.disconnect();
    }, [externalSocket, game_code, player_uuid]);

    useEffect(() => {
        const activeSocket = externalSocket || ownSocketRef.current;
        if (!activeSocket) return;
        const handleGameStats = (data) => {
            setGameState(data);
            setSelectedCardIdx(null);
            setSelectedCardIndices(new Set());
            setErrorMessage('');
        };
        const handleError = (data) => {
            console.error('Server error:', data);
            setErrorMessage(data.message || 'An error occurred');
        };
        activeSocket.on('game_stats', handleGameStats);
        activeSocket.on('error', handleError);
        return () => {
            activeSocket.off('game_stats', handleGameStats);
            activeSocket.off('error', handleError);
        };
    }, [externalSocket]);

    const phase = gameState.game_event_state || '';
    const phaseLabel = PHASE_LABELS[phase] || phase;
    const phaseClass = PHASE_CLASSES[phase] || '';
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
    const roundWinnerSide = gameState.round_winner_side || '';
    const roundDefenderPoints = gameState.round_defender_points || 0;
    const roundPromotionLevels = gameState.round_promotion_levels || 0;
    const roundPromotedPlayers = gameState.round_promoted_players || [];
    const gameWinner = gameState.game_winner || '';
    const isHost = gameState.hosting || false;
    const playerLevels = gameState.player_levels || {};

    // --- Trump Declaration ---
    const isTrumpPhase = phase === 'waiting-on-alpha-choose-trump';
    const canDeclareTrump = isTrumpPhase && isAlpha;

    const isEligibleTrumpCard = (card) => canDeclareTrump && card.rank === myLevel;

    const eligibleSuits = {};
    if (canDeclareTrump) {
        hand.forEach(card => {
            if (card.rank === myLevel && card.suit !== 'SMALL' && card.suit !== 'BIG') {
                eligibleSuits[card.suit] = (eligibleSuits[card.suit] || 0) + 1;
            }
        });
    }

    const handleCardClick = (idx) => {
        if (canDeclareTrump && isEligibleTrumpCard(hand[idx])) setSelectedCardIdx(idx);
    };

    const handleDeclareTrump = () => {
        if (selectedCardIdx === null || !socket) return;
        const card = hand[selectedCardIdx];
        socket.emit('declare_trump', { game_code, player_uuid, suit: card.suit, rank: card.rank });
        setSelectedCardIdx(null);
    };

    // --- Friend Calling ---
    const isFriendPhase = phase === 'waiting-on-alpha-friend-card-choice';
    const canCallFriends = isFriendPhase && isAlpha;

    useEffect(() => {
        if (canCallFriends && callingCards.length !== numFriendsToCall) {
            setCallingCards(Array.from({ length: numFriendsToCall }, () => ({ suit: 'CLUB', rank: 'ACE', order: 1 })));
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
        socket.emit('call_friends', { game_code, player_uuid, calling_cards: callingCards });
    };

    // --- Kitty Exchange ---
    const isKittyPhase = phase === 'waiting-on-alpha-kitty-sort';
    const canExchangeKitty = isKittyPhase && isAlpha;

    const toggleKittyCard = (idx) => {
        if (!canExchangeKitty) return;
        setSelectedCardIndices(prev => {
            const next = new Set(prev);
            if (next.has(idx)) next.delete(idx);
            else if (next.size < kittySize) next.add(idx);
            return next;
        });
    };

    const handleKittyExchange = () => {
        if (!socket) return;
        const discardedCards = Array.from(selectedCardIndices).map(idx => ({ suit: hand[idx].suit, rank: hand[idx].rank }));
        socket.emit('kitty_exchange', { game_code, player_uuid, discarded_cards: discardedCards });
        setSelectedCardIndices(new Set());
    };

    // --- Card Play ---
    const isPlayPhase = phase === 'round-started';
    const isLeading = isPlayPhase && myTurn && leadingHand.length === 0;
    const cardsToPlay = isLeading ? null : (leadingHand.length || 1);

    const handlePlayCardClick = (idx) => {
        if (!isPlayPhase || !myTurn) return;
        setSelectedCardIndices(prev => {
            const next = new Set(prev);
            if (next.has(idx)) next.delete(idx);
            else if (cardsToPlay === null || next.size < cardsToPlay) next.add(idx);
            return next;
        });
    };

    const handlePlayCard = () => {
        if (selectedCardIndices.size === 0 || !socket || !myTurn) return;
        const cards = Array.from(selectedCardIndices).map(idx => ({ suit: hand[idx].suit, rank: hand[idx].rank }));
        socket.emit('play_cards', { game_code, player_uuid, cards });
        setSelectedCardIndices(new Set());
    };

    const nonTrumpSuits = NON_TRUMP_SUITS.filter(s => s !== trumpSuit);
    const nonTrumpRanks = RANK_OPTIONS.filter(r => r !== trumpRank);

    return (
        <div className="game-container">
            {/* Header */}
            <div className="game-header">
                <div className="game-header-left">
                    <h2>Finding Friends</h2>
                    <span className="game-code-small">Game: {game_code}</span>
                </div>
                <div className="game-header-right">
                    <span className={`phase-badge ${phaseClass}`}>{phaseLabel}</span>
                    {trumpSuit && <div className="trump-info">Trump: {trumpRank} of {SUIT_SYMBOLS[trumpSuit] || trumpSuit}</div>}
                    {myLevel && <div style={{ fontSize: '0.85rem' }}>Your Level: {RANK_DISPLAY[myLevel] || myLevel}</div>}
                    {isAlpha && <div className="alpha-badge">You are the Alpha</div>}
                </div>
            </div>

            {/* Players bar */}
            <div className="players-bar">
                {playerList.map((player, idx) => {
                    const isCurrent = currentPlayer && currentPlayer.uuid === player.uuid;
                    const isMe = player.uuid === player_uuid;
                    return (
                        <div key={player.uuid || idx} className={`player-chip${isCurrent ? ' is-current' : ''}${isMe ? ' is-me' : ''}`}>
                            {player.name}
                            {isMe && ' (you)'}
                            {isCurrent && ' \u25C0'}
                        </div>
                    );
                })}
            </div>

            {/* Error banner */}
            {errorMessage && (
                <div className="info-panel error">
                    <span>{errorMessage}</span>
                    <button className="close-btn" onClick={() => setErrorMessage('')}>✕</button>
                </div>
            )}

            {/* Trump declaration */}
            {isTrumpPhase && !isAlpha && (
                <div className="info-panel waiting">Waiting for the alpha player to declare trump...</div>
            )}
            {canDeclareTrump && (
                <div className="info-panel action">
                    <h4>Declare Trump Suit</h4>
                    <p>Your level is <strong>{RANK_DISPLAY[myLevel] || myLevel}</strong>. Click a matching card below to select a trump suit, then confirm.</p>
                    {Object.keys(eligibleSuits).length === 0 && (
                        <>
                            <p className="error-text">You have no cards matching your level. Pick any suit:</p>
                            <div className="suit-picker">
                                {NON_TRUMP_SUITS.map(suit => (
                                    <button key={suit} className="suit-btn" onClick={() => {
                                        if (!socket) return;
                                        socket.emit('declare_trump', { game_code, player_uuid, suit, rank: myLevel });
                                    }}>
                                        {SUIT_SYMBOLS[suit]}
                                    </button>
                                ))}
                            </div>
                        </>
                    )}
                    {selectedCardIdx !== null && (
                        <button className="btn btn-orange" onClick={handleDeclareTrump}>
                            Declare {SUIT_SYMBOLS[hand[selectedCardIdx]?.suit] || ''} as Trump
                        </button>
                    )}
                </div>
            )}

            {/* Friend Calling */}
            {isFriendPhase && !isAlpha && (
                <div className="info-panel waiting">
                    Trump: <strong>{SUIT_SYMBOLS[trumpSuit] || trumpSuit} {trumpRank}</strong>. Waiting for alpha to call friends...
                </div>
            )}
            {canCallFriends && (
                <div className="info-panel action-blue">
                    <h4>Call {numFriendsToCall} Friend Card{numFriendsToCall > 1 ? 's' : ''}</h4>
                    <p>Specify which cards will reveal your secret partners. Called cards must not be trumps.</p>
                    {callingCards.map((cc, idx) => (
                        <div key={idx} className="friend-call-row">
                            <span style={{ fontWeight: 'bold' }}>#{idx + 1}</span>
                            <select value={cc.order} onChange={e => updateCallingCard(idx, 'order', parseInt(e.target.value))}>
                                <option value={1}>1st</option>
                                <option value={2}>2nd</option>
                                <option value={3}>3rd</option>
                                <option value={4}>4th</option>
                            </select>
                            <select value={cc.rank} onChange={e => updateCallingCard(idx, 'rank', e.target.value)}>
                                {nonTrumpRanks.map(r => <option key={r} value={r}>{r}</option>)}
                            </select>
                            <span>of</span>
                            <select value={cc.suit} onChange={e => updateCallingCard(idx, 'suit', e.target.value)}>
                                {nonTrumpSuits.map(s => <option key={s} value={s}>{SUIT_SYMBOLS[s]} {s}</option>)}
                            </select>
                        </div>
                    ))}
                    <button className="btn btn-secondary" onClick={handleCallFriends}>Confirm Friend Cards</button>
                </div>
            )}

            {/* Called cards strip */}
            {friendCallingCards.length > 0 && phase !== 'waiting-on-alpha-friend-card-choice' && (
                <div className="meta-strip">
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

            {/* Kitty Exchange */}
            {isKittyPhase && !isAlpha && (
                <div className="info-panel waiting">Waiting for alpha to exchange kitty cards...</div>
            )}
            {canExchangeKitty && (
                <div className="info-panel action">
                    <h4>Kitty Exchange</h4>
                    <p>The kitty ({kittySize} cards) has been added to your hand. Select {kittySize} cards to discard face-down.</p>
                    <p style={{ color: '#7f8c8d', fontSize: '0.85rem' }}>Selected: {selectedCardIndices.size} / {kittySize}</p>
                    {selectedCardIndices.size === kittySize && (
                        <button className="btn btn-primary" onClick={handleKittyExchange}>Confirm Discard</button>
                    )}
                </div>
            )}

            {/* Trick area */}
            {activePile.length > 0 && (
                <div className="trick-area">
                    <h4>Current Trick</h4>
                    <div className="trick-cards">
                        {activePile.map((card, idx) => <Card key={idx} card={card} selected={false} />)}
                    </div>
                </div>
            )}

            {/* Turn indicator + Play button */}
            {phase === 'round-started' && (
                <div>
                    <div className={`turn-indicator ${myTurn ? 'your-turn' : 'waiting-turn'}`}>
                        {myTurn
                            ? <>
                                {isLeading
                                    ? `It's your turn to lead! Select 1 or more cards.`
                                    : `It's your turn! Select ${cardsToPlay > 1 ? `${cardsToPlay} cards` : 'a card'} to play.`
                                }
                                {selectedCardIndices.size > 0 && (cardsToPlay === null
                                    ? ` (${selectedCardIndices.size} selected)`
                                    : ` (${selectedCardIndices.size}/${cardsToPlay} selected)`
                                )}
                              </>
                            : `Waiting for ${currentPlayer?.name || '...'} to play...`
                        }
                    </div>
                    {myTurn && selectedCardIndices.size > 0 && (cardsToPlay === null || selectedCardIndices.size === cardsToPlay) && (
                        <button className="btn btn-primary" style={{ width: 'auto', marginBottom: '10px' }} onClick={handlePlayCard}>
                            Play {selectedCardIndices.size} card{selectedCardIndices.size > 1 ? 's' : ''}
                        </button>
                    )}
                </div>
            )}

            {/* Revealed friends */}
            {revealedFriends.length > 0 && (
                <div className="meta-strip" style={{ background: 'rgba(232, 248, 245, 0.9)' }}>
                    <strong>Revealed Friends:</strong>{' '}
                    {revealedFriends.map((uuid, idx) => {
                        const p = playerList.find(pl => pl.uuid === uuid);
                        return <span key={uuid}>{idx > 0 && ', '}{p?.name || uuid}</span>;
                    })}
                </div>
            )}

            {/* Round scores */}
            {gameState.players_round_score && Object.keys(gameState.players_round_score).length > 0 && phase === 'round-started' && (
                <div className="scores-bar">
                    {playerList.map((player) => (
                        <span key={player.uuid}>
                            {player.name}: {gameState.players_round_score[player.uuid] || 0} pts
                        </span>
                    ))}
                </div>
            )}

            {/* Round ended summary */}
            {phase === 'round-ended' && (
                <div className="result-card">
                    <h3>Round Over!</h3>
                    <p>{onAlphaTeam ? 'You were on the Alpha team.' : 'You were on the Defender team.'}</p>
                    <p>
                        Defender points: <strong>{roundDefenderPoints}</strong>
                        {' \u2014 '}
                        {roundWinnerSide === 'trump_maker' && <span style={{ color: '#27ae60' }}>Trump makers win!</span>}
                        {roundWinnerSide === 'defender' && <span style={{ color: '#2980b9' }}>Defenders win!</span>}
                        {roundWinnerSide === 'none' && <span style={{ color: '#7f8c8d' }}>Draw - no one advances.</span>}
                    </p>
                    {roundPromotionLevels > 0 && (
                        <p>
                            <strong>+{roundPromotionLevels} level{roundPromotionLevels > 1 ? 's' : ''}</strong> for:{' '}
                            {roundPromotedPlayers.map((uuid, idx) => {
                                const p = playerList.find(pl => pl.uuid === uuid);
                                return <span key={uuid}>{idx > 0 && ', '}{p?.name || uuid}</span>;
                            })}
                        </p>
                    )}
                    <h4>Player Levels</h4>
                    <div className="level-chips">
                        {playerList.map(player => (
                            <span key={player.uuid} className={`level-chip${roundPromotedPlayers.includes(player.uuid) ? ' promoted' : ''}`}>
                                {player.name}: Lv {RANK_DISPLAY[playerLevels[player.uuid]] || playerLevels[player.uuid] || '?'}
                                {' '}({gameState.players_round_score?.[player.uuid] || 0} pts)
                            </span>
                        ))}
                    </div>
                    {isHost && (
                        <button className="btn btn-orange" style={{ marginTop: '12px' }} onClick={() => {
                            if (!socket) return;
                            socket.emit('next_round', { game_code, player_uuid });
                        }}>
                            Start Next Round
                        </button>
                    )}
                    {!isHost && <p style={{ color: '#7f8c8d', fontSize: '0.85rem', marginTop: '8px' }}>Waiting for the host to start the next round...</p>}
                </div>
            )}

            {/* Game over */}
            {phase === 'game-ended' && (
                <div className="result-card game-over">
                    <h3>Game Over!</h3>
                    <p style={{ fontSize: '1.1rem' }}>
                        {(() => {
                            const winner = playerList.find(p => p.uuid === gameWinner);
                            return winner ? `${winner.name} has passed Ace and wins the game!` : 'A player has won!';
                        })()}
                    </p>
                    <h4>Final Levels</h4>
                    <div className="level-chips">
                        {playerList.map(player => (
                            <span key={player.uuid} className={`level-chip${player.uuid === gameWinner ? ' winner' : ''}`}>
                                {player.name}: Lv {RANK_DISPLAY[playerLevels[player.uuid]] || playerLevels[player.uuid] || '?'}
                            </span>
                        ))}
                    </div>
                    {onLeaveGame && (
                        <button className="btn btn-primary" style={{ marginTop: '16px', width: 'auto' }} onClick={onLeaveGame}>
                            Back to Home
                        </button>
                    )}
                </div>
            )}

            {/* Hand */}
            <div className="hand-area">
                <h4>Your Hand ({hand.length} cards)</h4>
                <div className="hand-cards">
                    {hand.map((card, idx) => {
                        const eligible = isEligibleTrumpCard(card);
                        const selected = selectedCardIdx === idx || selectedCardIndices.has(idx);
                        const dimmed = canDeclareTrump && !eligible;

                        let onClick;
                        if (canDeclareTrump && eligible) onClick = () => handleCardClick(idx);
                        else if (canExchangeKitty) onClick = () => toggleKittyCard(idx);
                        else if (isPlayPhase && myTurn) onClick = () => handlePlayCardClick(idx);

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
