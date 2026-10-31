import { useState } from 'react';
import { LEVEL_LABELS, RANK_OPTIONS, RANK_LABELS } from '../../constants/cards';
import { SOCKET_EVENTS } from '../../api/events';

/* HR-13: between rounds the host may put next round's trump rank to a vote.
 * Optional, and nobody's level changes. The server counts the votes and the
 * majority; this only shows the state and sends the host's and voters' moves. */
const RankVote = ({ view, emit }) => {
    const [rank, setRank] = useState(RANK_OPTIONS[0]);

    if ((view.settings || {}).free_trump_choice) return null;

    const open = view.rank_proposal > 0;
    const passed = view.next_round_rank > 0;
    const label = (value) => LEVEL_LABELS[value] || value;
    const canVote = !view.hosting && !view.is_watcher;

    /* While a vote is open it takes over the screen, so nobody can miss that
     * the table is being asked something. A watcher has no say and nothing to
     * click, so they get a line in the page rather than a screen they cannot
     * get out of. */
    const overlay = open && !view.is_watcher && (
        <div className="rank-vote-overlay" role="dialog" aria-modal="true" aria-labelledby="rank-vote-title">
            <div className="rank-vote-dialog">
                <h3 id="rank-vote-title">Vote: next trump rank</h3>
                <p className="rank-vote-rank">{label(view.rank_proposal)}</p>
                <p>
                    {view.hosting
                        ? 'You proposed this rank for the next round. Waiting for the table to vote.'
                        : 'The host proposes this rank as trump for the next round.'}
                </p>
                <p className="rank-vote-tally">
                    {view.rank_vote_yes} of {view.rank_vote_of} agree — a majority passes it
                </p>
                {canVote && (
                    <div className="friend-call-row">
                        <button
                            type="button"
                            className={`btn btn-inline ${view.my_rank_vote === true ? 'btn-orange' : 'btn-secondary'}`}
                            aria-pressed={view.my_rank_vote === true}
                            onClick={() => emit(SOCKET_EVENTS.VOTE_RANK, { approve: true })}
                        >
                            Yes
                        </button>
                        <button
                            type="button"
                            className={`btn btn-inline ${view.my_rank_vote === false ? 'btn-orange' : 'btn-secondary'}`}
                            aria-pressed={view.my_rank_vote === false}
                            onClick={() => emit(SOCKET_EVENTS.VOTE_RANK, { approve: false })}
                        >
                            No
                        </button>
                    </div>
                )}
                {view.hosting && (
                    <button
                        type="button"
                        className="btn btn-secondary btn-inline"
                        onClick={() => emit(SOCKET_EVENTS.CANCEL_RANK_VOTE)}
                    >
                        Cancel vote
                    </button>
                )}
            </div>
        </div>
    );

    if (view.hosting) {
        return (
            <div className="rank-vote">
                {overlay}
                <h4>Next trump rank</h4>
                {passed && (
                    <>
                        <p>The table agreed: next round's trump rank is <strong>{label(view.next_round_rank)}</strong>.</p>
                        <button
                            type="button"
                            className="btn btn-secondary btn-inline"
                            onClick={() => emit(SOCKET_EVENTS.CANCEL_RANK_VOTE)}
                        >
                            Use normal levels instead
                        </button>
                    </>
                )}
                {!passed && (
                    <p>Optional: let the table vote on a different trump rank for the next round.</p>
                )}
                <div className="friend-call-row">
                    <select
                        aria-label="Proposed trump rank"
                        value={rank}
                        onChange={e => setRank(e.target.value)}
                    >
                        {RANK_OPTIONS.map(option => (
                            <option key={option} value={option}>{RANK_LABELS[option] || option}</option>
                        ))}
                    </select>
                    <button
                        type="button"
                        className="btn btn-secondary btn-inline"
                        onClick={() => emit(SOCKET_EVENTS.PROPOSE_RANK, { rank })}
                    >
                        {passed ? 'Propose a different rank' : 'Propose a rank'}
                    </button>
                </div>
            </div>
        );
    }

    if (!open && !passed) return null;

    return (
        <div className="rank-vote">
            {overlay}
            <h4>Next trump rank</h4>
            {open && view.is_watcher && (
                <p>
                    The host proposes <strong>{label(view.rank_proposal)}</strong> as trump for the
                    next round. {view.rank_vote_yes} of {view.rank_vote_of} agree.
                </p>
            )}
            {passed && (
                <p>The table agreed: next round's trump rank is <strong>{label(view.next_round_rank)}</strong>.</p>
            )}
        </div>
    );
};

export default RankVote;
