from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers.analytics_router import (
    router as analytics_router,
)
from app.routers.github_webhook_router import (
    router as github_webhook_router,
)
from app.routers.history_router import (
    router as history_router,
)
from app.routers.repository_router import (
    router as repository_router,
)
from app.services.database_service import init_db


FRONTEND_DIR = (
    Path(__file__).resolve().parent.parent
    / "frontend"
)


app = FastAPI(
    title="CodeSentry API",
    version="1.0.0",
    description="AI Powered Code Reviewer",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize SQLite tables.
init_db()


# API routers must be registered before the
# catch-all frontend static mount.
app.include_router(repository_router)
app.include_router(history_router)
app.include_router(github_webhook_router)
app.include_router(analytics_router)


@app.get("/api", tags=["Home"])
def home():
    return {
        "success": True,
        "message": "Welcome to CodeSentry API",
    }


# Keep this last because mounting at "/" catches
# frontend paths such as / and /index.html.
app.mount(
    "/",
    StaticFiles(
        directory=FRONTEND_DIR,
        html=True,
    ),
    name="frontend",
)