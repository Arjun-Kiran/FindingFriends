from pydantic import BaseModel, field_validator
from typing import Union
from uuid import uuid4, UUID


class Player(BaseModel):
    uuid: Union[str, UUID] = ''
    name: str = ''
    # Animal emoji shown beside the name everywhere this player appears.
    # Assigned at join time, so it is only ever empty for games saved before
    # avatars existed. See Game/Modules/Avatars.py.
    avatar: str = ''

    @field_validator('uuid')
    @classmethod
    def convert_uuid_to_str(cls, v) -> str:
        if isinstance(v, UUID):
            return str(v)
        if v != '':
            UUID(v, version=4)
            return str(v)
        return v


class PlayerPointer(BaseModel):
    index: int
    player_uuid: str

    @field_validator('player_uuid')
    @classmethod
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        
        if str(v) != '':
            UUID(v, version=4)
            return str(v)
        return str(v)
