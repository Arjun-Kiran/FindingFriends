/* Copying to the clipboard from a page that is not in a secure context.
 *
 * navigator.clipboard is exposed ONLY on https:// and on localhost/127.0.0.1.
 * A game served over plain http:// on a bare IP — which is what a droplet beta
 * is — has no navigator.clipboard at all, so reaching for
 * navigator.clipboard.writeText there throws
 *
 *     TypeError: can't access property "writeText", navigator.clipboard is undefined
 *
 * rather than failing politely. That is why the copy button works on localhost
 * and dies on the droplet.
 *
 * document.execCommand('copy') is deprecated, but it is the only thing that
 * works in an insecure context and every current browser still supports it.
 * So: try the modern API, fall back to the old one, and report failure so the
 * caller can tell the player to select the text by hand.
 */

const legacyCopy = (text) => {
    const textarea = document.createElement('textarea');
    textarea.value = text;
    // Off-screen but still selectable. display:none or visibility:hidden would
    // make the selection — and therefore the copy — silently fail.
    textarea.setAttribute('readonly', '');
    textarea.style.position = 'fixed';
    textarea.style.top = '0';
    textarea.style.left = '0';
    textarea.style.opacity = '0';
    document.body.appendChild(textarea);
    try {
        textarea.select();
        // iOS Safari ignores select() on a readonly field without this.
        textarea.setSelectionRange(0, text.length);
        return document.execCommand('copy');
    } catch {
        return false;
    } finally {
        document.body.removeChild(textarea);
    }
};

/** Copy `text`, returning whether it worked. Never throws. */
export const copyText = async (text) => {
    if (navigator.clipboard && window.isSecureContext) {
        try {
            await navigator.clipboard.writeText(text);
            return true;
        } catch {
            // Present but refused — a denied permission, or a browser that
            // blocks the write outside a user gesture. The legacy path often
            // still succeeds, so fall through rather than giving up.
        }
    }
    return legacyCopy(text);
};
