import { useState } from 'react';

export const CORNER = {
    LEFT: 'top-left',
    RIGHT: 'top-right',
};

const STORAGE_KEY = 'findingFriendsNotificationCorner';

/* Reads through a try/catch: storage throws outright in a private window or
 * when a browser is set to block site data, and a notification preference is
 * not worth taking the game down for. */
const readCorner = () => {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        return saved === CORNER.LEFT || saved === CORNER.RIGHT ? saved : CORNER.RIGHT;
    } catch {
        return CORNER.RIGHT;
    }
};

/** Which corner the player keeps their notifications in, remembered per browser. */
export const useNotificationCorner = () => {
    const [corner, setCorner] = useState(readCorner);

    const move = (next) => {
        setCorner(next);
        try {
            localStorage.setItem(STORAGE_KEY, next);
        } catch {
            // Preference lasts for this session only. Nothing else breaks.
        }
    };

    const toggle = () => move(corner === CORNER.RIGHT ? CORNER.LEFT : CORNER.RIGHT);

    return { corner, toggle };
};

const COLLAPSED_KEY = 'findingFriendsNotificationsCollapsed';

const readCollapsed = () => {
    try {
        return localStorage.getItem(COLLAPSED_KEY) === 'true';
    } catch {
        return false;
    }
};

/** Whether the player has folded the stack away, remembered per browser like the corner. */
export const useNotificationsCollapsed = () => {
    const [collapsed, setCollapsed] = useState(readCollapsed);

    const toggle = () => {
        const next = !collapsed;
        setCollapsed(next);
        try {
            localStorage.setItem(COLLAPSED_KEY, String(next));
        } catch {
            // Lasts for this session only, as the corner does.
        }
    };

    return { collapsed, toggle };
};
