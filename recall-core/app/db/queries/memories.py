import uuid

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Agent, Memory, MemoryLink, RetrievalEvent
from app.shortid import generate_short_id


async def insert_memory(
    db: AsyncSession,
    *,
    agent_id: uuid.UUID,
    content: str,
    tags: list[str],
    source_url: str | None,
    embedding: list[float],
    embedding_model: str,
    quality: int = 0,
) -> tuple[Memory, list[dict]]:
    """Insert memory, run dedup check, create links. Returns (memory, similar_list)."""
    short_id = generate_short_id()

    memory = Memory(
        agent_id=agent_id,
        short_id=short_id,
        content=content,
        tags=tags,
        source_url=source_url,
        embedding=embedding,
        embedding_model=embedding_model,
        quality=quality,
    )
    db.add(memory)
    await db.flush()

    vec_literal = "[" + ",".join(str(v) for v in embedding) + "]"
    stmt = text(
        "SELECT id, short_id, 1 - (embedding <=> CAST(:vec AS vector)) AS similarity"
        " FROM memories"
        " WHERE id != :mid AND quality > -2"
        " ORDER BY embedding <=> CAST(:vec AS vector)"
        " LIMIT 10"
    ).bindparams(vec=vec_literal, mid=memory.id)
    rows = (await db.execute(stmt)).fetchall()

    similar: list[dict] = []
    for row in rows:
        sim = float(row.similarity)
        if sim < settings.min_similarity:
            continue
        relation = "similar"
        if sim >= settings.duplicate_threshold:
            relation = "duplicate_candidate"
        if sim >= settings.auto_duplicate_threshold and memory.duplicate_of is None:
            memory.duplicate_of = row.id
        link = MemoryLink(
            memory_id=memory.id,
            related_id=row.id,
            relation=relation,
            similarity=sim,
        )
        db.add(link)
        similar.append({
            "id": row.id,
            "short_id": row.short_id,
            "similarity": round(sim, 4),
            "relation": relation,
        })

    await db.commit()
    await db.refresh(memory)
    return memory, similar


async def vector_search(
    db: AsyncSession,
    *,
    embedding: list[float],
    limit: int = 10,
) -> list[dict]:
    """Semantic search. Returns list of dicts with memory fields + similarity + retrieval_count."""
    vec_literal = "[" + ",".join(str(v) for v in embedding) + "]"
    stmt = text(
        "SELECT m.id, m.short_id, m.content, m.tags, m.source_url, m.created_at,"
        " a.name AS author_name,"
        " 1 - (m.embedding <=> CAST(:vec AS vector)) AS similarity,"
        " (SELECT count(*) FROM retrieval_events re WHERE re.memory_id = m.id) AS retrieval_count"
        " FROM memories m"
        " JOIN agents a ON a.id = m.agent_id"
        " WHERE m.quality > -2"
        " AND 1 - (m.embedding <=> CAST(:vec AS vector)) >= :min_sim"
        " ORDER BY m.embedding <=> CAST(:vec AS vector)"
        " LIMIT :lim"
    ).bindparams(vec=vec_literal, min_sim=settings.min_similarity, lim=limit)
    rows = (await db.execute(stmt)).fetchall()
    return [
        {
            "id": r.id,
            "short_id": r.short_id,
            "content": r.content,
            "tags": r.tags,
            "source_url": r.source_url,
            "created_at": r.created_at,
            "author_name": r.author_name,
            "similarity": round(float(r.similarity), 4),
            "retrieval_count": r.retrieval_count,
        }
        for r in rows
    ]


async def get_memory_by_id_or_short(db: AsyncSession, id_or_short: str) -> dict | None:
    """Get memory by UUID or short_id."""
    try:
        uid = uuid.UUID(id_or_short)
        where = "m.id = :val"
        val = uid
    except ValueError:
        where = "m.short_id = :val"
        val = id_or_short

    stmt = text(
        "SELECT m.id, m.short_id, m.content, m.tags, m.source_url, m.created_at,"
        " a.name AS author_name"
        " FROM memories m"
        " JOIN agents a ON a.id = m.agent_id"
        f" WHERE {where}"
    ).bindparams(val=val)
    row = (await db.execute(stmt)).fetchone()
    if row is None:
        return None

    links_stmt = text(
        "SELECT ml.related_id, m2.short_id, ml.relation, ml.similarity"
        " FROM memory_links ml"
        " JOIN memories m2 ON m2.id = ml.related_id"
        " WHERE ml.memory_id = :mid"
    ).bindparams(mid=row.id)
    links = (await db.execute(links_stmt)).fetchall()

    return {
        "id": row.id,
        "short_id": row.short_id,
        "content": row.content,
        "tags": row.tags,
        "source_url": row.source_url,
        "created_at": row.created_at,
        "author_name": row.author_name,
        "related": [
            {
                "id": l.related_id,
                "short_id": l.short_id,
                "relation": l.relation,
                "similarity": round(float(l.similarity), 4) if l.similarity else 0,
            }
            for l in links
        ],
    }
