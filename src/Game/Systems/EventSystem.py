from datetime import datetime
from typing import Dict
from Game.Modules.EventEnum import Event, EventItem
from uuid import uuid4


def build_event(event_type: Event, message: str) -> EventItem:
    utcnow = datetime.utcnow()
    return EventItem(event=event_type, message=message, time_stamp=str(utcnow.timestamp()), uuid=str(uuid4()))
