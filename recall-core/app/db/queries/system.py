from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SystemConfig


async def is_write_enabled(db: AsyncSession) -> bool:
    result = await db.execute(
        select(SystemConfig.value).where(SystemConfig.key == "global_write_enabled")
    )
    row = result.scalar_one_or_none()
    return row == "true" if row is not None else True


async def set_config(db: AsyncSession, key: str, value: str) -> None:
    now = datetime.now(timezone.utc)
    result = await db.execute(
        update(SystemConfig)
        .where(SystemConfig.key == key)
        .values(value=value, updated_at=now)
    )
    if result.rowcount == 0:
        db.add(SystemConfig(key=key, value=value, updated_at=now))
    await db.commit()


async def get_config(db: AsyncSession, key: str) -> str | None:
    result = await db.execute(
        select(SystemConfig.value).where(SystemConfig.key == key)
    )
    return result.scalar_one_or_none()
