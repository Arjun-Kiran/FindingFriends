import { describe, expect, test, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import RankVote from './RankVote';
import { SOCKET_EVENTS } from '../../api/events';

/* HR-13: the host's optional vote on next round's trump rank. The server
 * decides everything; these check what each person is shown and what they send. */
const view = (overrides = {}) => ({
    hosting: false,
    is_watcher: false,
    settings: {},
    rank_proposal: 0,
    rank_vote_yes: 0,
    rank_vote_of: 0,
    my_rank_vote: null,
    next_round_rank: 0,
    ...overrides,
});

const renderVote = (overrides) => {
    const emit = vi.fn();
    const result = render(<RankVote view={view(overrides)} emit={emit} />);
    return { emit, ...result };
};

describe('rank vote', () => {
    test('the host can propose a rank, and it defaults to nothing being open', () => {
        const { emit } = renderVote({ hosting: true });

        fireEvent.change(screen.getByLabelText('Proposed trump rank'), { target: { value: 'KING' } });
        fireEvent.click(screen.getByRole('button', { name: 'Propose a rank' }));

        expect(emit).toHaveBeenCalledWith(SOCKET_EVENTS.PROPOSE_RANK, { rank: 'KING' });
    });

    test('the host sees the tally and can cancel an open vote', () => {
        const { emit } = renderVote({ hosting: true, rank_proposal: 12, rank_vote_yes: 2, rank_vote_of: 4 });

        expect(screen.getByText(/2 of 4 agree/)).toBeTruthy();
        fireEvent.click(screen.getByRole('button', { name: 'Cancel vote' }));

        expect(emit).toHaveBeenCalledWith(SOCKET_EVENTS.CANCEL_RANK_VOTE);
    });

    test('the host can drop a rank that already passed', () => {
        const { emit } = renderVote({ hosting: true, next_round_rank: 12 });

        fireEvent.click(screen.getByRole('button', { name: 'Use normal levels instead' }));

        expect(emit).toHaveBeenCalledWith(SOCKET_EVENTS.CANCEL_RANK_VOTE);
    });

    test('an open vote covers the screen as a dialog, for the host and the voters', () => {
        const { unmount } = renderVote({ rank_proposal: 12, rank_vote_of: 4 });
        expect(screen.getByRole('dialog')).toBeTruthy();
        unmount();

        renderVote({ hosting: true, rank_proposal: 12, rank_vote_of: 4 });
        expect(screen.getByRole('dialog')).toBeTruthy();
    });

    test('no dialog while nothing is open, or for a watcher', () => {
        const { unmount } = renderVote({ hosting: true });
        expect(screen.queryByRole('dialog')).toBeNull();
        unmount();

        renderVote({ is_watcher: true, rank_proposal: 12, rank_vote_of: 4 });
        expect(screen.queryByRole('dialog')).toBeNull();
    });

    test('a player is shown nothing until a vote is open', () => {
        const { container } = renderVote();

        expect(container.firstChild).toBeNull();
    });

    test('a player votes yes or no', () => {
        const { emit } = renderVote({ rank_proposal: 12, rank_vote_yes: 1, rank_vote_of: 4 });

        fireEvent.click(screen.getByRole('button', { name: 'Yes' }));
        fireEvent.click(screen.getByRole('button', { name: 'No' }));

        expect(emit).toHaveBeenNthCalledWith(1, SOCKET_EVENTS.VOTE_RANK, { approve: true });
        expect(emit).toHaveBeenNthCalledWith(2, SOCKET_EVENTS.VOTE_RANK, { approve: false });
    });

    test('a watcher sees the vote but cannot cast one', () => {
        renderVote({ is_watcher: true, rank_proposal: 12, rank_vote_yes: 1, rank_vote_of: 4 });

        expect(screen.getByText(/host proposes/)).toBeTruthy();
        expect(screen.queryByRole('button', { name: 'Yes' })).toBeNull();
    });

    test('a passed rank is announced to everyone', () => {
        renderVote({ next_round_rank: 12 });

        expect(screen.getByText(/The table agreed/)).toBeTruthy();
    });

    test('a table with free trump choice has no rank to vote on', () => {
        const { container } = renderVote({ hosting: true, settings: { free_trump_choice: true } });

        expect(container.firstChild).toBeNull();
    });
});
