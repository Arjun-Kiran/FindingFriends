/* "4:07" for 247 seconds.
 *
 * Rounded up, so a countdown only reads 0:00 once its time is really up, and
 * never negative: a countdown that has run out says 0:00 until the server's
 * word that it has arrives. */
export const formatCountdown = (seconds) => {
    const whole = Math.max(0, Math.ceil(seconds));
    const minutes = Math.floor(whole / 60);
    return `${minutes}:${String(whole % 60).padStart(2, '0')}`;
};
