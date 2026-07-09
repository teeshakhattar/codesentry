import traceback

from fastapi import APIRouter, HTTPException

from app.schemas.repository_schema import RepositoryRequest
from app.services.git_service import clone_repository
from app.services.ai_reviewer import test_gemini
from app.services.review_service import (
    review_repository,
    review_repository_changes,
)


router = APIRouter(
    prefix="",
    tags=["Repository"]
)


@router.post("/review-repository")
def review_repository_endpoint(
    repository: RepositoryRequest
):
    print("FULL REVIEW REQUEST RECEIVED")

    try:
        repo_url = str(repository.repo_url)

        return review_repository(repo_url)

    except Exception as e:
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/review-repository/incremental")
def review_repository_incremental_endpoint(
    repository: RepositoryRequest
):
    print("INCREMENTAL REVIEW REQUEST RECEIVED")

    try:
        repo_url = str(repository.repo_url)

        return review_repository_changes(
            repo_url=repo_url,
            base_ref="HEAD~1",
            target_ref="HEAD",
        )

    except Exception as e:
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/clone")
def clone_repo(
    repository: RepositoryRequest
):
    try:
        repo_url = str(repository.repo_url)

        return clone_repository(repo_url)

    except Exception as e:
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/test-ai")
def test_ai_endpoint():
    try:
        return {
            "success": True,
            "response": test_gemini()
        }

    except Exception as e:
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )