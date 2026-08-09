from datetime import datetime
from typing import Dict
from Game.Modules.EventEnum import Event, EventItem
from uuid import uuid4


# Events are stored with the game state and only ever used to show the most
# recent notification, so old ones are dead weight in every database write. A
# flapping connection can generate them quickly, hence the cap.
MAX_EVENTS = 50


def build_event(event_type: Event, message: str) -> EventItem:
    utcnow = datetime.utcnow()
    return EventItem(event=event_type, message=message, time_stamp=str(utcnow.timestamp()), uuid=str(uuid4()))


def record_event(game_state, event_type: Event, message: str) -> EventItem:
    """Append an event to the game, dropping the oldest once past MAX_EVENTS."""
    event = build_event(event_type, message)
    game_state.events.append(event)
    if len(game_state.events) > MAX_EVENTS:
        del game_state.events[:-MAX_EVENTS]
    return event
