from dataclasses import dataclass
from uuid import uuid4

@dataclass
class Player():
    uuid: str = str(uuid4())
    name: str = ''
