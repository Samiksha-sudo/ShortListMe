from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import cvs, health
from app.core.config import settings

@asynccontextmanager
async def lifespan(_: FastAPI):
    command.upgrade(Config("alembic.ini"), "head")
    yield


app = FastAPI(title="ShortlistMe API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health.router)
app.include_router(cvs.router)
