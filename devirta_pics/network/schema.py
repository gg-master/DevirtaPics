from typing import Optional

from pydantic import BaseModel, Field, PositiveInt, root_validator, validator

AVAILABLE_TYPES = ['auth', 'mode', 'close', 'stop']
AVAILABLE_MODES = ['test', 'rehab']


class BaseReq(BaseModel):
    type: str

    @validator('type')
    def available_type(cls, v):
        if v not in AVAILABLE_TYPES:
            raise ValueError('Not available type of command.')
        return v


class AuthReq(BaseReq):
    type: str
    token: str


class CommandsReq(BaseReq):
    type: str
    mode: Optional[str]
    time: Optional[PositiveInt]

    @root_validator
    def available_mode(cls, values):
        if values.get('type') in ['stop', 'close']:
            return values
        mode, time = values.get('mode'), values.get('time')
        if mode not in AVAILABLE_MODES:
            raise ValueError('Not available mode.')
        if mode == 'test':
            if time is None:
                raise ValueError('Mode `test` must have `time` parameter.')
            if not isinstance(time, int):
                raise ValueError('Invalid time.')
        return values
