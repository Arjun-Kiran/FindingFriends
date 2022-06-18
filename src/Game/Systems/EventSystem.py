from datetime import datetime
from typing import Dict
from Game.Modules.EventEnum import Event


def build_event_dict(event_type: Event, message: str) -> Dict:
    utcnow = datetime.utcnow()
    return {
        "time_utc": utcnow.isoformat(),
        "time_epoch": utcnow.timestamp(),
        "message": message,
        "event": event_type.value
    }
