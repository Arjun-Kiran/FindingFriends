import { render, screen, fireEvent } from '@testing-library/react';
import AvatarPicker from './AvatarPicker';

const CHOICES = ['🦊', '🐻', '🐼', '🐨'];

const renderPicker = (props = {}) => {
    const onChoose = vi.fn();
    const utils = render(
        <AvatarPicker choices={CHOICES} taken={[]} mine="" onChoose={onChoose} {...props} />
    );
    return { onChoose, ...utils };
};

const option = (glyph) => screen.getByRole('button', { name: glyph });

test('renders one button per offered avatar', () => {
    renderPicker();

    CHOICES.forEach(glyph => expect(option(glyph)).toBeInTheDocument());
});

test('renders nothing when the server offered no choices', () => {
    const { container } = render(<AvatarPicker choices={[]} onChoose={vi.fn()} />);

    expect(container).toBeEmptyDOMElement();
});

test('sends the picked avatar', () => {
    const { onChoose } = renderPicker();

    fireEvent.click(option('🐼'));

    expect(onChoose).toHaveBeenCalledWith('🐼');
});

test('avatars held by other players cannot be picked', () => {
    renderPicker({ taken: ['🐻'] });

    expect(option('🐻')).toBeDisabled();
    expect(option('🐻')).toHaveClass('is-taken');
    expect(option('🦊')).toBeEnabled();
});

/* Your own avatar is in `taken` too — it would otherwise grey itself out the
   moment the server echoed your pick back. */
test('your own avatar reads as selected, not as unavailable', () => {
    renderPicker({ taken: ['🦊', '🐻'], mine: '🦊' });

    expect(option('🦊')).toHaveClass('is-mine');
    expect(option('🦊')).not.toHaveClass('is-taken');
    expect(option('🦊')).toHaveAttribute('aria-pressed', 'true');
});

test('nothing can be picked while the connection is down', () => {
    renderPicker({ disabled: true });

    CHOICES.forEach(glyph => expect(option(glyph)).toBeDisabled());
});
