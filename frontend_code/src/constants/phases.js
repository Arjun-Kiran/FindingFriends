/* Game phases, mirroring the backend GameEventState enum values. */

export const PHASE = {
    WAITING_FOR_PLAYERS: 'waiting-for-player-to-join',
    CHOOSE_TRUMP: 'waiting-on-alpha-choose-trump',
    CALL_FRIENDS: 'waiting-on-alpha-friend-card-choice',
    KITTY_SORT: 'waiting-on-alpha-kitty-sort',
    ROUND_STARTED: 'round-started',
    ROUND_ENDED: 'round-ended',
    GAME_ENDED: 'game-ended',
};

export const PHASE_LABELS = {
    [PHASE.CHOOSE_TRUMP]: 'Trump Declaration',
    [PHASE.CALL_FRIENDS]: 'Friend Calling',
    [PHASE.KITTY_SORT]: 'Kitty Exchange',
    [PHASE.ROUND_STARTED]: 'Round in Progress',
    [PHASE.ROUND_ENDED]: 'Round Ended',
    [PHASE.GAME_ENDED]: 'Game Over',
};

export const PHASE_CLASSES = {
    [PHASE.CHOOSE_TRUMP]: 'trump',
    [PHASE.CALL_FRIENDS]: 'friend',
    [PHASE.KITTY_SORT]: 'kitty',
    [PHASE.ROUND_STARTED]: 'playing',
    [PHASE.ROUND_ENDED]: 'ended',
    [PHASE.GAME_ENDED]: 'ended',
};

export const phaseLabel = (phase) => PHASE_LABELS[phase] || phase;
export const phaseClass = (phase) => PHASE_CLASSES[phase] || '';
