import uuid
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class AgentInfo(BaseModel):
    id: uuid.UUID
    name: str


class RegisterResponse(BaseModel):
    agent: AgentInfo
    api_key: str
