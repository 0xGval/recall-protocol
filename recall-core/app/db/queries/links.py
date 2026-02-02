import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MemoryLink


async def create_link(
    db: AsyncSession,
    *,
    memory_id: uuid.UUID,
    related_id: uuid.UUID,
    relation: str,
    similarity: float | None = None,
) -> MemoryLink:
    link = MemoryLink(
        memory_id=memory_id,
        related_id=related_id,
        relation=relation,
        similarity=similarity,
    )
    db.add(link)
    await db.commit()
    return link
