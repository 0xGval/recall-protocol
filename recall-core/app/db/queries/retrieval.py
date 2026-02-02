import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RetrievalEvent


async def log_retrieval(
    db: AsyncSession,
    *,
    agent_id: uuid.UUID,
    memory_id: uuid.UUID,
    query: str,
    similarity: float,
) -> None:
    event = RetrievalEvent(
        agent_id=agent_id,
        memory_id=memory_id,
        query=query,
        similarity=similarity,
    )
    db.add(event)
    await db.commit()
