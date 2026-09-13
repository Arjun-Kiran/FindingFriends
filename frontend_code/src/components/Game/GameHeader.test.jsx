import { render, screen, fireEvent, act } from '@testing-library/react';
import GameHeader from './GameHeader';
import { copyText } from '../../utils/copyText';
import { playerView } from '../../test-utils/playerView';

vi.mock('../../utils/copyText', () => ({ copyText: vi.fn() }));

const renderHeader = () => render(
    <GameHeader view={playerView({ game_event_state: 'round-started' })} gameCode="below-adopt-havoc" onLeaveGame={vi.fn()} />
);

beforeEach(() => copyText.mockReset());

describe('sharing the game code mid-game', () => {
    test('copies the code, so someone can come and watch or ask for a seat', async () => {
        copyText.mockResolvedValue(true);
        renderHeader();

        fireEvent.click(screen.getByRole('button', { name: 'Copy' }));

        expect(await screen.findByRole('button', { name: 'Copied!' })).toBeInTheDocument();
        expect(copyText).toHaveBeenCalledWith('below-adopt-havoc');
    });

    test('says so in words when copying is impossible, and how to do it by hand', async () => {
        copyText.mockResolvedValue(false);
        renderHeader();

        fireEvent.click(screen.getByRole('button', { name: 'Copy' }));

        const failed = await screen.findByRole('button', { name: 'Copy failed' });
        expect(failed).toHaveAttribute('title', expect.stringMatching(/copy it yourself/));
    });

    test('goes back to Copy after a moment', async () => {
        vi.useFakeTimers();
        copyText.mockResolvedValue(true);
        renderHeader();

        await act(async () => {
            fireEvent.click(screen.getByRole('button', { name: 'Copy' }));
        });
        expect(screen.getByRole('button', { name: 'Copied!' })).toBeInTheDocument();

        act(() => vi.advanceTimersByTime(3000));

        expect(screen.getByRole('button', { name: 'Copy' })).toBeInTheDocument();
        vi.useRealTimers();
    });
});
