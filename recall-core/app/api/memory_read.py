from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_agent
from app.db.models import Agent
from app.db.queries.memories import vector_search, get_memory_by_id_or_short
from app.db.queries.retrieval import log_retrieval
from app.embedding.client import embedding_client
from app.ratelimit.limiter import check_rate_limit
from app.schemas.memories import (
    AuthorInfo,
    MemoryDetail,
    MemoryGetResponse,
    MemorySearchResponse,
    MemorySearchResult,
    RelatedMemory,
)

router = APIRouter()


@router.get("/memory/search", response_model=MemorySearchResponse)
async def search_memories(
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(10, ge=1, le=50),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    if not await check_rate_limit(str(agent.id), "memory:search", agent.trust_level):
        raise HTTPException(status_code=429, detail="Rate limit exceeded for search")

    vector = await embedding_client.embed(q)
    rows = await vector_search(db, embedding=vector, limit=limit)

    for r in rows:
        await log_retrieval(
            db,
            agent_id=agent.id,
            memory_id=r["id"],
            query=q,
            similarity=r["similarity"],
        )

    return MemorySearchResponse(
        query=q,
        results=[
            MemorySearchResult(
                id=r["id"],
                short_id=r["short_id"],
                content=r["content"],
                tags=r["tags"],
                source_url=r["source_url"],
                author=AuthorInfo(name=r["author_name"]),
                created_at=r["created_at"],
                similarity=r["similarity"],
                retrieval_count=r["retrieval_count"],
            )
            for r in rows
        ],
    )


@router.get("/memory/{memory_id}", response_model=MemoryGetResponse)
async def get_memory(
    memory_id: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    if not await check_rate_limit(str(agent.id), "memory:get", agent.trust_level):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    data = await get_memory_by_id_or_short(db, memory_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    return MemoryGetResponse(
        memory=MemoryDetail(
            id=data["id"],
            short_id=data["short_id"],
            content=data["content"],
            tags=data["tags"],
            source_url=data["source_url"],
            author=AuthorInfo(name=data["author_name"]),
            created_at=data["created_at"],
            related=[RelatedMemory(**r) for r in data["related"]],
        )
    )
