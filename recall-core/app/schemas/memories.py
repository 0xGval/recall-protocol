import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class MemoryWriteRequest(BaseModel):
    content: str = Field(..., min_length=80)
    tags: list[str] = Field(..., min_length=2, max_length=6)
    source_url: str | None = None


class SimilarMemory(BaseModel):
    id: uuid.UUID
    short_id: str
    similarity: float
    relation: str


class MemoryWriteResponse(BaseModel):
    success: bool = True
    id: uuid.UUID
    short_id: str
    status: str = "saved"
    similar: list[SimilarMemory] = []


class AuthorInfo(BaseModel):
    name: str


class MemorySearchResult(BaseModel):
    id: uuid.UUID
    short_id: str
    content: str
    tags: list[str]
    source_url: str | None
    author: AuthorInfo
    created_at: datetime
    similarity: float
    retrieval_count: int


class MemorySearchResponse(BaseModel):
    success: bool = True
    query: str
    results: list[MemorySearchResult]


class RelatedMemory(BaseModel):
    id: uuid.UUID
    short_id: str
    relation: str
    similarity: float


class MemoryDetail(BaseModel):
    id: uuid.UUID
    short_id: str
    content: str
    tags: list[str]
    source_url: str | None
    author: AuthorInfo
    created_at: datetime
    related: list[RelatedMemory] = []


class MemoryGetResponse(BaseModel):
    success: bool = True
    memory: MemoryDetail
