from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.keys import hash_api_key
from app.db.engine import async_session
from app.db.models import Agent


async def get_db():
    async with async_session() as session:
        yield session


async def get_current_agent(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Agent:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    key = auth.removeprefix("Bearer ").strip()
    key_hash = hash_api_key(key)

    result = await db.execute(select(Agent).where(Agent.api_key_hash == key_hash))
    agent = result.scalar_one_or_none()

    if agent is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    if agent.disabled_at is not None:
        raise HTTPException(status_code=403, detail="Agent is disabled")

    return agent
