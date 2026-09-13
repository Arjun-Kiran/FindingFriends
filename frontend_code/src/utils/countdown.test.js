import { formatCountdown } from './countdown';

test('reads as minutes and seconds', () => {
    expect(formatCountdown(247)).toBe('4:07');
    expect(formatCountdown(60)).toBe('1:00');
});

test('rounds up, so 0:00 means the time is really up', () => {
    expect(formatCountdown(0.2)).toBe('0:01');
});

test('never goes below zero', () => {
    expect(formatCountdown(-5)).toBe('0:00');
});
