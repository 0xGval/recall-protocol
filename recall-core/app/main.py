from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.engine import engine
from app.api.router import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(title="Recall", version="0.1.0", lifespan=lifespan)
app.include_router(api_router, prefix="/api/v1")
