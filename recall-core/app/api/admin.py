import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_agent
from app.db.models import Agent, Memory
from app.db.queries.system import set_config

router = APIRouter(prefix="/admin", tags=["admin"])


def require_core(agent: Agent) -> Agent:
    if agent.trust_level < 2:
        raise HTTPException(status_code=403, detail="Requires trust_level >= 2")
    return agent


@router.post("/heartbeat")
async def admin_heartbeat(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    require_core(agent)
    now = datetime.now(timezone.utc).isoformat()
    await set_config(db, "last_admin_heartbeat", now)
    await set_config(db, "global_write_enabled", "true")
    return {"success": True, "heartbeat": now, "global_write_enabled": True}


@router.post("/quarantine/{agent_id}")
async def quarantine_agent(
    agent_id: uuid.UUID,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
):
    require_core(agent)

    # Disable the agent
    result = await db.execute(
        update(Agent)
        .where(Agent.id == agent_id)
        .values(disabled_at=datetime.now(timezone.utc))
    )
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Mark all their memories as quarantined
    await db.execute(
        update(Memory)
        .where(Memory.agent_id == agent_id)
        .values(quality=-2)
    )
    await db.commit()

    return {"success": True, "agent_id": str(agent_id), "status": "quarantined"}
