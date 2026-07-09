import json
from typing import Any

from fastapi import (
    APIRouter,
    Header,
    HTTPException,
    Request,
)

from app.services.github_pr_formatter import (
    build_pull_request_comment,
)
from app.services.github_pr_service import (
    GitHubPRServiceError,
    post_pull_request_comment,
)
from app.services.github_webhook_service import (
    verify_github_signature,
)
from app.services.review_service import (
    review_repository_changes,
)


router = APIRouter(
    prefix="/webhooks/github",
    tags=["GitHub Webhooks"],
)


@router.post("")
async def github_webhook_endpoint(
    request: Request,
    x_github_event: str | None = Header(
        default=None,
        alias="X-GitHub-Event",
    ),
    x_github_delivery: str | None = Header(
        default=None,
        alias="X-GitHub-Delivery",
    ),
    x_hub_signature_256: str | None = Header(
        default=None,
        alias="X-Hub-Signature-256",
    ),
) -> dict[str, Any]:
    """
    Receive and verify GitHub webhook events.

    Supported flows:
    - push:
      runs incremental review between before/after SHAs
    - pull_request:
      runs incremental review between base/head SHAs
      and posts a CodeSentry summary comment
    - unsupported events:
      ignored safely
    """

    if not x_github_event:
        raise HTTPException(
            status_code=400,
            detail="Missing X-GitHub-Event header.",
        )

    payload_body = await request.body()

    try:
        signature_valid = verify_github_signature(
            payload_body=payload_body,
            signature_header=x_hub_signature_256,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        ) from exc

    if not signature_valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid GitHub webhook signature.",
        )

    try:
        payload = json.loads(payload_body)
    except (
        json.JSONDecodeError,
        UnicodeDecodeError,
        TypeError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload.",
        ) from exc

    print(
        f"Verified GitHub webhook received: "
        f"event={x_github_event}, "
        f"delivery={x_github_delivery or 'unknown'}"
    )

    # -------------------------------------------------
    # PUSH EVENT FLOW
    # -------------------------------------------------

    if x_github_event == "push":
        repository = payload.get(
            "repository",
            {},
        )

        repository_name = repository.get(
            "full_name"
        )

        repository_clone_url = repository.get(
            "clone_url"
        )

        before_sha = payload.get(
            "before"
        )

        after_sha = payload.get(
            "after"
        )

        ref = payload.get(
            "ref"
        )

        deleted = payload.get(
            "deleted",
            False,
        )

        if deleted:
            return {
                "success": True,
                "status": "ignored",
                "reason": "Deleted branch push.",
                "event_type": x_github_event,
                "delivery_id": x_github_delivery,
                "ref": ref,
            }

        if not repository_name:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Missing repository full_name "
                    "in push payload."
                ),
            )

        if not repository_clone_url:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Missing repository clone_url "
                    "in push payload."
                ),
            )

        if not before_sha or not after_sha:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Missing before or after SHA "
                    "in push payload."
                ),
            )

        zero_sha = "0" * 40

        if before_sha == zero_sha:
            return {
                "success": True,
                "status": "ignored",
                "reason": (
                    "New branch push has no valid "
                    "before commit for incremental review."
                ),
                "event_type": x_github_event,
                "delivery_id": x_github_delivery,
                "repository": repository_name,
                "ref": ref,
                "before_sha": before_sha,
                "after_sha": after_sha,
            }

        print(
            f"Triggering push incremental review: "
            f"repository={repository_name}, "
            f"base={before_sha}, "
            f"head={after_sha}"
        )

        try:
            review_result = review_repository_changes(
                repo_url=repository_clone_url,
                base_ref=before_sha,
                target_ref=after_sha,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Push incremental review failed: "
                    f"{exc}"
                ),
            ) from exc

        return {
            "success": True,
            "status": "push_review_completed",
            "event_type": x_github_event,
            "delivery_id": x_github_delivery,
            "repository": repository_name,
            "repository_clone_url": repository_clone_url,
            "ref": ref,
            "before_sha": before_sha,
            "after_sha": after_sha,
            "review_result": review_result,
        }

    # -------------------------------------------------
    # PULL REQUEST EVENT FLOW
    # -------------------------------------------------

    if x_github_event == "pull_request":
        action = payload.get(
            "action"
        )

        supported_actions = {
            "opened",
            "synchronize",
            "reopened",
        }

        if action not in supported_actions:
            return {
                "success": True,
                "status": "ignored",
                "reason": (
                    "Unsupported pull request action."
                ),
                "event_type": x_github_event,
                "delivery_id": x_github_delivery,
                "action": action,
            }

        repository = payload.get(
            "repository",
            {},
        )

        pull_request = payload.get(
            "pull_request",
            {},
        )

        repository_name = repository.get(
            "full_name"
        )

        repository_clone_url = repository.get(
            "clone_url"
        )

        pull_request_number = payload.get(
            "number"
        )

        base_sha = (
            pull_request
            .get("base", {})
            .get("sha")
        )

        head_sha = (
            pull_request
            .get("head", {})
            .get("sha")
        )

        if not repository_name:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Missing repository full_name "
                    "in webhook payload."
                ),
            )

        if not repository_clone_url:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Missing repository clone_url "
                    "in webhook payload."
                ),
            )

        if not pull_request_number:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Missing pull request number "
                    "in webhook payload."
                ),
            )

        if not base_sha or not head_sha:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Missing base or head SHA "
                    "in webhook payload."
                ),
            )

        print(
            f"Triggering PR incremental review: "
            f"repository={repository_name}, "
            f"base={base_sha}, "
            f"head={head_sha}"
        )

        try:
            review_result = review_repository_changes(
                repo_url=repository_clone_url,
                base_ref=base_sha,
                target_ref=head_sha,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=(
                    f"Incremental review failed: "
                    f"{exc}"
                ),
            ) from exc

        try:
            comment_body = build_pull_request_comment(
                review_result
            )

            github_comment = post_pull_request_comment(
                repository_full_name=repository_name,
                pull_request_number=pull_request_number,
                comment_body=comment_body,
            )

        except GitHubPRServiceError as exc:
            raise HTTPException(
                status_code=502,
                detail=(
                    f"Review completed, but GitHub "
                    f"PR comment failed: {exc}"
                ),
            ) from exc

        return {
            "success": True,
            "status": "review_completed_and_commented",
            "event_type": x_github_event,
            "delivery_id": x_github_delivery,
            "action": action,
            "repository": repository_name,
            "repository_clone_url": repository_clone_url,
            "pull_request_number": pull_request_number,
            "base_sha": base_sha,
            "head_sha": head_sha,
            "github_comment": {
                "id": github_comment.get("id"),
                "html_url": github_comment.get("html_url"),
            },
            "review_result": review_result,
        }

    # -------------------------------------------------
    # UNSUPPORTED EVENT FLOW
    # -------------------------------------------------

    return {
        "success": True,
        "status": "ignored",
        "reason": "Unsupported GitHub event.",
        "event_type": x_github_event,
        "delivery_id": x_github_delivery,
    }