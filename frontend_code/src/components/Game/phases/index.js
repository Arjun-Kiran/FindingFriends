import { PHASE } from '../../../constants/phases';
import TrumpDeclaration, { handRules as trumpHandRules } from './TrumpDeclaration';
import FriendCalling from './FriendCalling';
import KittyExchange, { handRules as kittyHandRules } from './KittyExchange';
import PlayPhase, {
    handRules as playHandRules,
    handAction as playHandAction,
    handNote as playHandNote,
} from './PlayPhase';
import RoundSummary from './RoundSummary';
import GameOver from './GameOver';

/* Adding a phase means adding one file and one entry here.
 *
 * `Panel`      — what to render for that phase.
 * `handRules`  — how the hand behaves during it (omit for "not interactive").
 *                See Hand.js for the shape: { selectable, dim, max, single }.
 * `handAction` — the phase's confirm button, drawn in the hand area beside the
 *                cards it acts on rather than in the panel. Omit for none.
 * `handNote`   — what to tell the player when the playable highlight has
 *                nothing to narrow down. Omit for none. */
export const PHASE_REGISTRY = {
    [PHASE.CHOOSE_TRUMP]: { Panel: TrumpDeclaration, handRules: trumpHandRules },
    [PHASE.CALL_FRIENDS]: { Panel: FriendCalling },
    [PHASE.KITTY_SORT]: { Panel: KittyExchange, handRules: kittyHandRules },
    [PHASE.ROUND_STARTED]: {
        Panel: PlayPhase,
        handRules: playHandRules,
        handAction: playHandAction,
        handNote: playHandNote,
    },
    [PHASE.ROUND_ENDED]: { Panel: RoundSummary },
    [PHASE.GAME_ENDED]: { Panel: GameOver },
};

export const phaseFor = (phase) => PHASE_REGISTRY[phase] || {};
