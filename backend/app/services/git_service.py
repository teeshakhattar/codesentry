from pathlib import Path

from git import Repo, GitCommandError


CLONE_DIRECTORY = Path("sample_repositories")


def _get_current_commit_sha(repo: Repo) -> str:
    """
    Return the full SHA of the repository's current HEAD commit.
    """
    return repo.head.commit.hexsha


def clone_repository(repo_url):
    """
    Clone a repository when it is not available locally.

    If the repository already exists locally, fetch updates from
    its remote and fast-forward the currently checked-out branch.

    Returns repository metadata including the exact current
    commit SHA that CodeSentry will review.
    """

    # Convert Pydantic HttpUrl to a normal string.
    repo_url = str(repo_url)

    if not repo_url:
        raise ValueError(
            "Repository URL cannot be empty."
        )

    CLONE_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    repository_name = (
        repo_url
        .rstrip("/")
        .split("/")[-1]
        .replace(".git", "")
    )

    destination = (
        CLONE_DIRECTORY
        / repository_name
    )

    try:
        # -----------------------------------------------------
        # EXISTING LOCAL REPOSITORY
        # -----------------------------------------------------
        if destination.exists():
            repo = Repo(destination)

            if repo.bare:
                raise ValueError(
                    f"Repository at {destination} is bare "
                    f"and cannot be reviewed."
                )

            # Fetch latest remote references.
            origin = repo.remotes.origin
            origin.fetch()

            # Update the currently checked-out branch safely.
            # pull() performs a normal Git fast-forward/merge
            # according to the repository state.
            if not repo.head.is_detached:
                origin.pull()

            commit_sha = _get_current_commit_sha(repo)

            return {
                "success": True,
                "status": "updated",
                "repository": repository_name,
                "path": str(destination),
                "commit_sha": commit_sha,
            }

        # -----------------------------------------------------
        # NEW REPOSITORY
        # -----------------------------------------------------
        repo = Repo.clone_from(
            repo_url,
            destination,
        )

        commit_sha = _get_current_commit_sha(repo)

        return {
            "success": True,
            "status": "cloned",
            "repository": repository_name,
            "path": str(destination),
            "commit_sha": commit_sha,
        }

    except GitCommandError as e:
        raise Exception(
            f"Git operation failed: {e}"
        )

    except Exception as e:
        raise Exception(
            f"Unexpected error while preparing repository: {e}"
        )