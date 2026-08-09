"""Application logging.

Never log game state. A dump of the state contains every player's hand and the
trump maker's hidden friends, so anyone with log access could see the whole
table. Log identifiers (game code, player uuid, event name) instead.
"""
import logging
import os
import sys

LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO').upper()

LOG_FORMAT = '%(asctime)s %(levelname)-8s %(name)s: %(message)s'


def configure_logging():
    """Set up root logging once, at process start."""
    root = logging.getLogger()
    if root.handlers:
        # Already configured (gunicorn, or a re-import under the reloader).
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    root.addHandler(handler)
    root.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))

    # These are noisy at DEBUG and log per-packet payloads.
    logging.getLogger('engineio').setLevel(logging.WARNING)
    logging.getLogger('socketio').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
