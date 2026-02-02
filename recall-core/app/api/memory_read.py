import hashlib
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_agent
from app.db.models import Agent
from app.db.queries.memories import vector_search, get_memory_by_id_or_short
from app.db.queries.retrieval import log_retrieval
from app.embedding.client import embedding_client
from app.ratelimit.limiter import check_rate_limit, get_redis
from app.schemas.memories import (
    AuthorInfo,
    MemoryDetail,
    MemoryGetResponse,
    MemorySearchResponse,
    MemorySearchResult,
    RelatedMemory,
)

router = APIRouter()

SEARCH_CACHE_TTL = 120  # seconds


def _cache_key(q: str, limit: int) -> str:
    h = hashlib.sha256(f"{q}:{limit}".encode()).hexdigest()[:16]
    return f"search_cache:{h}"


@router.get("/memory/search", response_model=MemorySearchResponse)
async def search_memories(
    q: str = Query(..., min_length=1, max_length=500),
    limit: int = Query(10, ge=1, le=50),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    allowed, retry_after = await check_rate_limit(str(agent.id), "memory:search", agent.trust_level)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded for search", "retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    # Check cache
    r = await get_redis()
    ck = _cache_key(q, limit)
    cached = await r.get(ck)

    if cached:
        rows = json.loads(cached)
    else:
        vector = await embedding_client.embed(q)
        rows = await vector_search(db, embedding=vector, limit=limit)
        # Serialize for cache (convert datetimes to strings)
        for row in rows:
            row["created_at"] = row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else row["created_at"]
            row["id"] = str(row["id"])
        await r.set(ck, json.dumps(rows), ex=SEARCH_CACHE_TTL)

    # Log retrieval events (always, even on cache hit)
    for row in rows:
        await log_retrieval(
            db,
            agent_id=agent.id,
            memory_id=row["id"],
            query=q,
            similarity=row["similarity"],
        )

    return MemorySearchResponse(
        query=q,
        results=[
            MemorySearchResult(
                id=row["id"],
                short_id=row["short_id"],
                content=row["content"],
                tags=row["tags"],
                source_url=row["source_url"],
                author=AuthorInfo(name=row["author_name"]),
                created_at=row["created_at"],
                similarity=row["similarity"],
                retrieval_count=row["retrieval_count"],
            )
            for row in rows
        ],
    )


@router.get("/memory/{memory_id}", response_model=MemoryGetResponse)
async def get_memory(
    memory_id: str,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    allowed, retry_after = await check_rate_limit(str(agent.id), "memory:get", agent.trust_level)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded", "retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

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
