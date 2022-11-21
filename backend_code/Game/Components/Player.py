from pydantic import BaseModel, validator
from typing import Union
from uuid import uuid4, UUID


class Player(BaseModel):
    uuid: Union[str, UUID] = ''
    name: str = ''

    @validator('uuid')
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

    @validator('player_uuid')
    def convert_uuid_to_str(cls, v):
        if isinstance(v, UUID):
            return str(v)
        
        if str(v) != '':
            raise ValueError("Invalid value for player_uuid")
        return str(v)
