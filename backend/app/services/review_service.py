import time
from pathlib import Path

from app.services.git_service import clone_repository
from app.services.repository_scanner import scan_repository
from app.services.file_reader import read_repository_files
from app.services.ai_reviewer import review_code, review_diff
from app.services.scoring_service import score_repository
from app.services.database_service import save_scan, get_connection
from app.services.diff_parser import get_changed_files
from app.services.function_extractor import (
    get_changed_functions_for_file,
)


REQUEST_DELAY_SECONDS = 2


def _get_previous_commit_sha(repo_url: str):
    """
    Return the most recent stored commit SHA for this repository.

    Older scans created before commit tracking was added may have
    commit_sha = NULL. Those scans are skipped automatically.
    """
    conn = get_connection()

    try:
        row = conn.execute(
            """
            SELECT commit_sha
            FROM scans
            WHERE repo_url = ?
              AND commit_sha IS NOT NULL
              AND commit_sha != ''
            ORDER BY scanned_at DESC, id DESC
            LIMIT 1
            """,
            (str(repo_url),),
        ).fetchone()

        if not row:
            return None

        return row["commit_sha"]

    finally:
        conn.close()


def _perform_full_review(
    repo_url: str,
    clone_result: dict,
):
    """
    Review every supported non-empty file in the repository.
    """
    repository_path = Path(clone_result["path"])
    commit_sha = clone_result["commit_sha"]

    file_paths = scan_repository(repository_path)
    files = read_repository_files(file_paths)

    reviews = []

    reviewable_files = [
        file
        for file in files
        if file.get("content", "").strip()
    ]

    for index, file in enumerate(reviewable_files):
        print(f"Full review: {file['file']}")

        try:
            review = review_code(
                file["content"]
            )

        except Exception as e:
            import traceback

            traceback.print_exc()

            review = (
                f"Review failed: {repr(e)}"
            )

        reviews.append(
            {
                "file": file["file"],
                "review": review,
            }
        )

        if index < len(reviewable_files) - 1:
            time.sleep(REQUEST_DELAY_SECONDS)

    scored = score_repository(reviews)

    result = {
        "repository": clone_result["repository"],
        "review_mode": "full",
        "commit_sha": commit_sha,
        "files_reviewed": len(reviews),
        "repository_risk_score": (
            scored["repository_risk_score"]
        ),
        "repository_risk_band": (
            scored["repository_risk_band"]
        ),
        "files_scored": scored["files_scored"],
        "files_failed": scored["files_failed"],
        "reviews": scored["reviews"],
    }

    scan_id = save_scan(
        repo_url,
        result,
    )

    result["scan_id"] = scan_id

    return result


def _perform_incremental_review(
    repo_url: str,
    clone_result: dict,
    base_ref: str,
    target_ref: str,
):
    """
    Review only changed code between two Git commits.

    For changed Python files:
    - map Git diff hunks to AST function/method spans
    - review only affected functions where possible

    Fallback:
    - if no affected Python function can be extracted,
      review the original diff hunks
    """
    repository_path = Path(clone_result["path"])

    changed_files = get_changed_files(
        repository_path=repository_path,
        base_ref=base_ref,
        target_ref=target_ref,
    )

    reviews = []

    reviewable_changes = [
        changed_file
        for changed_file in changed_files
        if changed_file.get("hunks")
    ]

    for index, changed_file in enumerate(
        reviewable_changes
    ):
        file_path = (
            changed_file.get("new_path")
            or changed_file.get("old_path")
            or "unknown"
        )

        hunks = changed_file["hunks"]

        absolute_file_path = (
            repository_path / file_path
        )

        print(
            f"Incremental review: {file_path}"
        )

        changed_functions = []

        try:
            changed_functions = (
                get_changed_functions_for_file(
                    file_path=absolute_file_path,
                    hunks=hunks,
                )
            )

        except Exception:
            import traceback

            traceback.print_exc()

            changed_functions = []

        # AST-focused path:
        # review only affected Python functions.
        if changed_functions:
            function_reviews = []

            for function_index, function in enumerate(
                changed_functions
            ):
                function_name = function["name"]
                function_source = function["source"]

                print(
                    f"  AST affected function: "
                    f"{function_name} "
                    f"({function['start_line']}-"
                    f"{function['end_line']})"
                )

                try:
                    function_review = review_code(
                        function_source
                    )

                except Exception as e:
                    import traceback

                    traceback.print_exc()

                    function_review = (
                        f"Review failed: {repr(e)}"
                    )

                function_reviews.append(
                    {
                        "name": function_name,
                        "start_line": (
                            function["start_line"]
                        ),
                        "end_line": (
                            function["end_line"]
                        ),
                        "is_async": function["is_async"],
                        "review": function_review,
                    }
                )

                if (
                    function_index
                    < len(changed_functions) - 1
                ):
                    time.sleep(
                        REQUEST_DELAY_SECONDS
                    )

            reviews.append(
                {
                    "file": file_path,
                    "change_type": changed_file.get(
                        "change_type",
                        "modified",
                    ),
                    "review_scope": "affected_functions",
                    "changed_functions": [
                        {
                            "name": function["name"],
                            "start_line": (
                                function["start_line"]
                            ),
                            "end_line": (
                                function["end_line"]
                            ),
                            "is_async": (
                                function["is_async"]
                            ),
                        }
                        for function in changed_functions
                    ],
                    "review": function_reviews,
                }
            )

        # Safe fallback:
        # non-Python file, syntax error, module-level change,
        # deleted file, or no function overlap.
        else:
            print(
                f"  No affected AST function found. "
                f"Using diff review fallback."
            )

            try:
                review = review_diff(
                    file_path=file_path,
                    hunks=hunks,
                )

            except Exception as e:
                import traceback

                traceback.print_exc()

                review = (
                    f"Review failed: {repr(e)}"
                )

            reviews.append(
                {
                    "file": file_path,
                    "change_type": changed_file.get(
                        "change_type",
                        "modified",
                    ),
                    "review_scope": "diff_fallback",
                    "changed_functions": [],
                    "review": review,
                }
            )

        if index < len(reviewable_changes) - 1:
            time.sleep(REQUEST_DELAY_SECONDS)

    scored = score_repository(reviews)

    result = {
        "repository": clone_result["repository"],
        "review_mode": "incremental",
        "base_ref": base_ref,
        "target_ref": target_ref,
        "commit_sha": target_ref,
        "changed_files_count": len(changed_files),
        "files_reviewed": len(reviews),
        "repository_risk_score": (
            scored["repository_risk_score"]
        ),
        "repository_risk_band": (
            scored["repository_risk_band"]
        ),
        "files_scored": scored["files_scored"],
        "files_failed": scored["files_failed"],
        "reviews": scored["reviews"],
    }

    scan_id = save_scan(
        repo_url,
        result,
    )

    result["scan_id"] = scan_id

    return result


def _perform_no_change_review(
    repo_url: str,
    clone_result: dict,
):
    """
    Store a lightweight scan result when the repository HEAD
    is identical to the last reviewed commit.
    """
    commit_sha = clone_result["commit_sha"]

    result = {
        "repository": clone_result["repository"],
        "review_mode": "no_changes",
        "commit_sha": commit_sha,
        "changed_files_count": 0,
        "files_reviewed": 0,
        "repository_risk_score": None,
        "repository_risk_band": "Unknown",
        "files_scored": 0,
        "files_failed": 0,
        "reviews": [],
    }

    scan_id = save_scan(
        repo_url,
        result,
    )

    result["scan_id"] = scan_id

    return result


def review_repository(repo_url: str):
    """
    Main CodeSentry review entry point.

    Behaviour:

    1. Prepare or update the local repository.
    2. Read the current Git commit SHA.
    3. Look up the last successfully stored reviewed commit.
    4. Choose full, incremental, or no-change review mode.
    """
    repo_url = str(repo_url)

    clone_result = clone_repository(repo_url)

    current_commit_sha = clone_result.get(
        "commit_sha"
    )

    if not current_commit_sha:
        raise RuntimeError(
            "Could not determine the repository HEAD commit."
        )

    previous_commit_sha = _get_previous_commit_sha(
        repo_url
    )

    print(
        f"Previous reviewed commit: "
        f"{previous_commit_sha or 'None'}"
    )

    print(
        f"Current repository commit: "
        f"{current_commit_sha}"
    )

    if previous_commit_sha is None:
        print(
            "No previous reviewed commit found. "
            "Running full repository review."
        )

        return _perform_full_review(
            repo_url=repo_url,
            clone_result=clone_result,
        )

    if previous_commit_sha == current_commit_sha:
        print(
            "Repository HEAD matches the previous "
            "reviewed commit. No changes detected."
        )

        return _perform_no_change_review(
            repo_url=repo_url,
            clone_result=clone_result,
        )

    print(
        "New repository commit detected. "
        "Running incremental review."
    )

    return _perform_incremental_review(
        repo_url=repo_url,
        clone_result=clone_result,
        base_ref=previous_commit_sha,
        target_ref=current_commit_sha,
    )


def review_repository_changes(
    repo_url: str,
    base_ref: str = "HEAD~1",
    target_ref: str = "HEAD",
):
    """
    Explicit incremental-review entry point.

    Kept for the existing temporary test endpoint and for
    future manual commit-range review support.
    """
    repo_url = str(repo_url)

    clone_result = clone_repository(repo_url)

    return _perform_incremental_review(
        repo_url=repo_url,
        clone_result=clone_result,
        base_ref=base_ref,
        target_ref=target_ref,
    )