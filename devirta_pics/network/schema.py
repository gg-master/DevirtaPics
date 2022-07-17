from typing import Optional

from pydantic import BaseModel, validator, Field, root_validator

AVAILABLE_TYPES = ['auth', 'mode', 'close']
AVAILABLE_MODES = ['test', 'rehab']


class BaseReq(BaseModel):
    type: str

    @validator('type')
    def available_type(cls, v):
        if v not in AVAILABLE_TYPES:
            raise ValueError('Not available type of command.')
        return v


class AuthReq(BaseReq):
    type: str = 'auth'
    token: str


class CommandsReq(BaseReq):
    type: str
    mode: Optional[str]
    time: Optional[int] = Field(ge=1)

    @root_validator
    def available_mode(cls, values):
        mode, time = values.get('mode'), values.get('time')
        if mode not in AVAILABLE_MODES:
            raise ValueError('Not available mode.')
        if mode == 'test' and time is None:
            raise ValueError('Mode `test` must have `time` parameter.')
        return values
