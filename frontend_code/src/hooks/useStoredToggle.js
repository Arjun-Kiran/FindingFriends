import { useCallback, useEffect, useState } from 'react';

/* A yes/no display preference that outlives the page.
 *
 * Preferences only — nothing here may decide what is legal or what gets sent
 * to the server. Storage that refuses to answer (a private window, a full
 * quota) falls back to the default rather than failing, because a preference
 * is never worth breaking a hand over. */
export const useStoredToggle = (key, initial = false) => {
    const [on, setOn] = useState(() => {
        try {
            const saved = localStorage.getItem(key);
            return saved === null ? initial : saved === 'true';
        } catch {
            return initial;
        }
    });

    useEffect(() => {
        try {
            localStorage.setItem(key, String(on));
        } catch {
            /* Lasts for this session only. */
        }
    }, [key, on]);

    return [on, useCallback(() => setOn(previous => !previous), [])];
};
