import { useCallback, useEffect, useRef, useState } from 'react';
import { copyText } from '../utils/copyText';

/* How long "Copied!" or "Copy failed" stays on the button. */
export const COPY_FEEDBACK_MS = 3000;

/* A copy button's state: 'idle', 'copied' or 'failed', back to 'idle' after a
 * moment.
 *
 * Copy can genuinely fail: navigator.clipboard does not exist over plain
 * http:// on an IP, which is how a droplet beta is reached, so this reports
 * failure rather than pretending — see utils/copyText.js. Whatever is being
 * copied is on screen either way. */
export const useCopyState = (text) => {
    const [state, setState] = useState('idle');
    const timer = useRef(null);

    useEffect(() => () => clearTimeout(timer.current), []);

    const copy = useCallback(async () => {
        const copied = await copyText(text);
        setState(copied ? 'copied' : 'failed');
        clearTimeout(timer.current);
        timer.current = setTimeout(() => setState('idle'), COPY_FEEDBACK_MS);
    }, [text]);

    return [state, copy];
};
