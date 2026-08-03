import { useEffect, useState } from 'react';

/* Which cards in the hand are currently picked.
 *
 * One Set covers every phase: trump declaration passes `single`, kitty and
 * following a trick pass `max`, leading passes neither. `resetKey` clears the
 * selection whenever it changes — pass the game state so a server push always
 * starts the player fresh. */
export const useCardSelection = (resetKey) => {
    const [selected, setSelected] = useState(() => new Set());

    useEffect(() => {
        setSelected(new Set());
    }, [resetKey]);

    const toggle = (index, { max = null, single = false } = {}) => {
        setSelected(previous => {
            if (single) {
                return previous.has(index) ? new Set() : new Set([index]);
            }
            const next = new Set(previous);
            if (next.has(index)) {
                next.delete(index);
            } else if (max === null || next.size < max) {
                next.add(index);
            }
            return next;
        });
    };

    const clear = () => setSelected(new Set());

    return {
        selected,
        toggle,
        clear,
        indices: [...selected],
        count: selected.size,
    };
};
