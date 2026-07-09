import os
from typing import Any

import requests


GITHUB_API_BASE_URL = "https://api.github.com"


class GitHubPRServiceError(Exception):
    """Raised when CodeSentry cannot communicate with GitHub."""


def get_github_token() -> str:
    """
    Read the GitHub API token from the environment.

    The token is used only for authenticated outbound
    requests from CodeSentry to GitHub.
    """
    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise GitHubPRServiceError(
            "GITHUB_TOKEN is not configured."
        )

    return token


def build_github_headers() -> dict[str, str]:
    """
    Build headers required for authenticated GitHub API calls.
    """
    token = get_github_token()

    return {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "CodeSentry-AI-Code-Reviewer",
    }


def post_pull_request_comment(
    repository_full_name: str,
    pull_request_number: int,
    comment_body: str,
) -> dict[str, Any]:
    """
    Post a CodeSentry summary comment to a GitHub pull request.

    GitHub treats pull request conversation comments
    as issue comments, so this uses:

    POST /repos/{owner}/{repo}/issues/{issue_number}/comments
    """
    if not repository_full_name:
        raise GitHubPRServiceError(
            "Repository full name is required."
        )

    if not pull_request_number:
        raise GitHubPRServiceError(
            "Pull request number is required."
        )

    if not comment_body.strip():
        raise GitHubPRServiceError(
            "Comment body cannot be empty."
        )

    url = (
        f"{GITHUB_API_BASE_URL}"
        f"/repos/{repository_full_name}"
        f"/issues/{pull_request_number}"
        f"/comments"
    )

    try:
        response = requests.post(
            url,
            headers=build_github_headers(),
            json={
                "body": comment_body,
            },
            timeout=20,
        )
    except requests.RequestException as exc:
        raise GitHubPRServiceError(
            f"GitHub API request failed: {exc}"
        ) from exc

    if response.status_code != 201:
        try:
            error_detail = response.json()
        except ValueError:
            error_detail = response.text

        raise GitHubPRServiceError(
            "GitHub rejected the PR comment request. "
            f"Status={response.status_code}, "
            f"Response={error_detail}"
        )

    try:
        return response.json()
    except ValueError as exc:
        raise GitHubPRServiceError(
            "GitHub returned an invalid JSON response."
        ) from exc