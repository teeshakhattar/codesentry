from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.repository_router import router as repository_router

app = FastAPI(
    title="CodeSentry API",
    version="1.0.0",
    description="AI Powered Code Reviewer"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repository_router)
from pathlib import Path
from fastapi.staticfiles import StaticFiles

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
from app.services.database_service import init_db
from app.routers.history_router import router as history_router

init_db()  # call this once, anywhere after app = FastAPI(...) is created

app.include_router(history_router)  # add alongside your existing app.include_router(repository_router) line
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")

@app.get("/", tags=["Home"])
def home():
    return {
        "success": True,
        "message": "Welcome to CodeSentry API"
    }
