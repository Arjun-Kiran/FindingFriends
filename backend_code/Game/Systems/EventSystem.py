from datetime import datetime, timezone
from typing import Dict
from Game.Modules.EventEnum import Event, EventItem
from uuid import uuid4


# Events are stored with the game state and only ever used to show the most
# recent notification, so old ones are dead weight in every database write. A
# flapping connection can generate them quickly, hence the cap.
MAX_EVENTS = 50


def build_event(event_type: Event, message: str, player_uuid: str = '') -> EventItem:
    # Aware, not datetime.utcnow(): that returns a naive datetime, and
    # .timestamp() reads naive datetimes as local time — which put every event
    # out by the UTC offset. Deprecated since Python 3.12 besides.
    now = datetime.now(timezone.utc)
    return EventItem(event=event_type, message=message, time_stamp=str(now.timestamp()),
                     uuid=str(uuid4()), player_uuid=str(player_uuid))


def record_event(game_state, event_type: Event, message: str, player_uuid: str = '') -> EventItem:
    """Append an event to the game, dropping the oldest once past MAX_EVENTS.

    `player_uuid` names the player the event is about, where there is one."""
    event = build_event(event_type, message, player_uuid)
    game_state.events.append(event)
    if len(game_state.events) > MAX_EVENTS:
        del game_state.events[:-MAX_EVENTS]
    return event
