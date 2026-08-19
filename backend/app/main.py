from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text

from app.database import Base, async_session, engine
from app.models import GoogleToken, MealTemplate  # noqa: F401  (ensure models registered)
from app.seed import seed_default_data

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup (if migration hasn't run) and seed defaults."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with async_session() as session:
        await seed_default_data(session)
    yield


app = FastAPI(title="FitTrack API", version="1.0.0", lifespan=lifespan)

# CORS — allow all origins during Phase 1
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


# --- Register routers ---
from app.routes.auth import router as auth_router, google_router as auth_google_router
from app.routes.day_entries import router as day_entries_router
from app.routes.meals import router as meals_router, templates_router as meal_templates_router
from app.routes.photos import router as photos_router
from app.routes.stats import router as stats_router
from app.routes.sync import router as sync_router
from app.routes.todos import router as todos_router
from app.routes.training import router as training_router
from app.routes.vision import router as vision_router

app.include_router(auth_router, prefix="/api")
app.include_router(auth_google_router, prefix="/api")
app.include_router(day_entries_router, prefix="/api")
app.include_router(meals_router, prefix="/api")
app.include_router(meal_templates_router, prefix="/api")
app.include_router(todos_router, prefix="/api")
app.include_router(training_router, prefix="/api")
app.include_router(sync_router, prefix="/api")
app.include_router(photos_router, prefix="/api")
app.include_router(vision_router, prefix="/api")
app.include_router(stats_router, prefix="/api")