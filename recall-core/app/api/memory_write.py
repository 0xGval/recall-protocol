from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_agent
from app.config import settings
from app.db.models import Agent
from app.db.queries.memories import insert_memory
from app.db.queries.system import is_write_enabled
from app.embedding.client import embedding_client
from app.ratelimit.limiter import check_rate_limit
from app.schemas.memories import MemoryWriteRequest, MemoryWriteResponse, SimilarMemory

router = APIRouter()


@router.post("/memory", response_model=MemoryWriteResponse)
async def write_memory(
    body: MemoryWriteRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    if not await is_write_enabled(db):
        raise HTTPException(status_code=503, detail="Writes are temporarily disabled")

    allowed, retry_after = await check_rate_limit(str(agent.id), "memory:write", agent.trust_level)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded for memory writes", "retry_after": retry_after},
            headers={"Retry-After": str(retry_after)},
        )

    quality = -1 if agent.trust_level == 0 else 0

    vector = await embedding_client.embed(body.content)

    memory, similar = await insert_memory(
        db,
        agent_id=agent.id,
        content=body.content,
        tags=body.tags,
        source_url=body.source_url,
        embedding=vector,
        embedding_model=f"openai/{settings.embedding_model}",
        quality=quality,
    )

    return MemoryWriteResponse(
        id=memory.id,
        short_id=memory.short_id,
        similar=[SimilarMemory(**s) for s in similar],
    )
