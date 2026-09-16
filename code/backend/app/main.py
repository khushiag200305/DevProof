"""
DevProof backend entrypoint.

Assembles the FastAPI app from its routers. Business logic lives in
app/services/, persistence models in app/models.py, and each feature
area gets its own router under app/routers/.

Run with:
    uvicorn app.main:app --reload
"""
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models  # noqa: F401  (import registers models on Base.metadata)
from .database import Base, engine
from .routers import auth as auth_router
from .routers import candidates as candidates_router
from .routers import github as github_router
from .routers import resume as resume_router
from .routers import score as score_router

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Dev-time convenience: create any missing tables against DATABASE_URL
    on startup. A real migration tool (Alembic) should replace this
    before the schema needs to evolve without data loss.
    """
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:  # pragma: no cover - depends on local DB availability
        print(f"Warning: could not connect to the database on startup: {exc}")
    yield


app = FastAPI(title="DevProof API", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    """Basic liveness check used by CI and manual smoke testing."""
    return {"status": "ok", "service": "devproof-backend"}


app.include_router(auth_router.router)
app.include_router(candidates_router.router)
app.include_router(resume_router.router)
app.include_router(github_router.router)
app.include_router(score_router.router)
