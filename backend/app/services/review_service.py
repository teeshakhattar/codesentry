import time
from pathlib import Path
from app.services.git_service import clone_repository
from app.services.repository_scanner import scan_repository
from app.services.file_reader import read_repository_files
from app.services.ai_reviewer import review_code
from app.services.scoring_service import score_repository
from app.services.database_service import save_scan

REQUEST_DELAY_SECONDS = 2


def review_repository(repo_url: str):

    clone_result = clone_repository(repo_url)

    repository_path = Path(clone_result["path"])

    file_paths = scan_repository(repository_path)

    files = read_repository_files(file_paths)

    reviews = []

    for index, file in enumerate(files):

        print(f"Reviewing: {file['file']}")

        if not file["content"].strip():
            continue

        try:
            review = review_code(file["content"])

        except Exception as e:
            import traceback

            traceback.print_exc()

            review = f"Review failed: {repr(e)}"

        reviews.append(
            {
                "file": file["file"],
                "review": review
            }
        )

        if index < len(files) - 1:
            time.sleep(REQUEST_DELAY_SECONDS)

    scored = score_repository(reviews)

    result = {
        "repository": clone_result["repository"],
        "files_reviewed": len(reviews),
        "repository_risk_score": scored["repository_risk_score"],
        "repository_risk_band": scored["repository_risk_band"],
        "files_scored": scored["files_scored"],
        "files_failed": scored["files_failed"],
        "reviews": scored["reviews"],
    }

    scan_id = save_scan(repo_url, result)
    result["scan_id"] = scan_id

    return result