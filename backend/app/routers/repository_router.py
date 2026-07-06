from pathlib import Path
import traceback

from fastapi import APIRouter, HTTPException

from app.schemas.repository_schema import RepositoryRequest
from app.services.git_service import clone_repository
from app.services.repository_scanner import scan_repository
from app.services.file_reader import read_repository_files
from app.services.ai_reviewer import test_gemini, review_code
from app.services.review_service import review_repository


router = APIRouter(prefix="", tags=["Repository"])


@router.post("/review-repository")
def review_repository_endpoint(repository: RepositoryRequest):
    print("REQUEST RECEIVED")

    try:
        # Convert Pydantic HttpUrl to normal Python string
        repo_url = str(repository.repo_url)

        return review_repository(repo_url)

    except Exception as e:
        traceback.print_exc()

        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@router.post("/clone")
def clone_repo(repository: RepositoryRequest):
    try:
        # Convert HttpUrl to string here too
        repo_url = str(repository.repo_url)

        return clone_repository(repo_url)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/scan")
def scan():
    repository_path = Path("sample_repositories/flask")

    if not repository_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Repository not found: {repository_path}"
        )

    return scan_repository(repository_path)


@router.get("/read-files")
def read_files():
    repository_path = Path("sample_repositories/flask")

    if not repository_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Repository not found: {repository_path}"
        )

    file_paths = scan_repository(repository_path)

    return read_repository_files(file_paths)


@router.get("/test-ai")
def test_ai():
    try:
        response = test_gemini()

        return {
            "success": True,
            "response": response
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/review-test")
def review_test():
    sample_code = """
def add(a, b):
    return a + b
"""

    try:
        review = review_code(sample_code)

        return {
            "success": True,
            "review": review
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }