from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Agent


async def create_agent(db: AsyncSession, *, name: str, api_key_hash: str) -> Agent:
    agent = Agent(name=name, api_key_hash=api_key_hash)
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent
