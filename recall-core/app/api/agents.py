from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.keys import generate_api_key, hash_api_key
from app.db.queries.agents import create_agent
from app.schemas.agents import RegisterRequest, RegisterResponse, AgentInfo

router = APIRouter()


@router.post("/agents/register", response_model=RegisterResponse)
async def register_agent(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    agent = await create_agent(db, name=body.name, api_key_hash=key_hash)
    return RegisterResponse(
        agent=AgentInfo(id=agent.id, name=agent.name),
        api_key=raw_key,
    )
