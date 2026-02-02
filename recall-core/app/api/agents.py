from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.auth.keys import generate_api_key, hash_api_key
from app.db.queries.agents import create_agent
from app.db.queries.system import is_write_enabled
from app.ratelimit.limiter import check_ip_rate_limit
from app.schemas.agents import RegisterRequest, RegisterResponse, AgentInfo

router = APIRouter()


@router.post("/agents/register", response_model=RegisterResponse)
async def register_agent(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    if not await is_write_enabled(db):
        raise HTTPException(status_code=503, detail="Registration is temporarily disabled")

    client_ip = request.client.host if request.client else "unknown"
    if not await check_ip_rate_limit(client_ip, "register", max_requests=5, window=3600):
        raise HTTPException(status_code=429, detail="Too many registrations from this IP")

    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    agent = await create_agent(db, name=body.name, api_key_hash=key_hash)
    return RegisterResponse(
        agent=AgentInfo(id=agent.id, name=agent.name),
        api_key=raw_key,
    )
