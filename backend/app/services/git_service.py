from pathlib import Path
from git import Repo, GitCommandError

CLONE_DIRECTORY = Path("sample_repositories")


def clone_repository(repo_url):

    # Convert Pydantic HttpUrl to normal string
    repo_url = str(repo_url)

    if not repo_url:
        raise ValueError("Repository URL cannot be empty.")

    CLONE_DIRECTORY.mkdir(parents=True, exist_ok=True)

    repository_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")

    destination = CLONE_DIRECTORY / repository_name

    if destination.exists():
        return {
            "success": True,
            "status": "already_exists",
            "repository": repository_name,
            "path": str(destination)
        }

    try:
        Repo.clone_from(repo_url, destination)

        return {
            "success": True,
            "status": "success",
            "repository": repository_name,
            "path": str(destination)
        }

    except GitCommandError as e:
        raise Exception(f"Git clone failed: {e}")

    except Exception as e:
        raise Exception(f"Unexpected error while cloning repository: {e}")