import { useEffect, useState } from 'react';

const TOAST_DURATION_MS = 4000;

/* Surfaces the newest server event as a short-lived notification.
 *
 * Events are things that happen away from the player's own actions — someone
 * joining, leaving, or losing connection — so they need announcing rather than
 * waiting to be noticed. */
export const useEventToast = (events) => {
    const [toastMessage, setToastMessage] = useState('');

    const latest = events && events.length > 0 ? events[events.length - 1] : null;
    // Depend on primitives, not the event object, so a re-fetch of identical
    // state doesn't re-trigger the toast.
    const latestUuid = latest && latest.uuid;
    const latestMessage = latest && latest.message;

    useEffect(() => {
        if (!latestMessage) {
            return undefined;
        }

        setToastMessage(latestMessage);
        const timer = setTimeout(() => setToastMessage(''), TOAST_DURATION_MS);

        return () => clearTimeout(timer);
    }, [latestUuid, latestMessage]);

    return toastMessage;
};
