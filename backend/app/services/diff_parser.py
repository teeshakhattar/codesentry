import re
import subprocess
from pathlib import Path
from typing import Any


DIFF_HEADER_PATTERN = re.compile(
    r"^diff --git a/(?P<old_path>.+?) b/(?P<new_path>.+)$"
)

HUNK_HEADER_PATTERN = re.compile(
    r"^@@ -(?P<old_start>\d+)(?:,(?P<old_count>\d+))? "
    r"\+(?P<new_start>\d+)(?:,(?P<new_count>\d+))? @@"
)


def get_git_diff(
    repository_path: Path,
    base_ref: str = "HEAD~1",
    target_ref: str = "HEAD",
) -> str:
    """
    Return the unified Git diff between two refs.

    Raises RuntimeError if Git cannot produce the diff.
    """
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repository_path),
            "diff",
            "--unified=0",
            "--no-color",
            base_ref,
            target_ref,
            "--",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if result.returncode != 0:
        error_message = result.stderr.strip() or "Unknown Git diff error"
        raise RuntimeError(
            f"Failed to generate diff for "
            f"{base_ref}..{target_ref}: {error_message}"
        )

    return result.stdout


def parse_git_diff(diff_text: str) -> list[dict[str, Any]]:
    """
    Parse unified Git diff text into structured file and hunk data.
    """
    changed_files = []
    current_file = None
    current_hunk = None

    for line in diff_text.splitlines():
        file_match = DIFF_HEADER_PATTERN.match(line)

        if file_match:
            current_file = {
                "old_path": file_match.group("old_path"),
                "new_path": file_match.group("new_path"),
                "hunks": [],
            }

            changed_files.append(current_file)
            current_hunk = None
            continue

        if current_file is None:
            continue

        if line.startswith("new file mode "):
            current_file["change_type"] = "added"
            continue

        if line.startswith("deleted file mode "):
            current_file["change_type"] = "deleted"
            continue

        if line.startswith("rename from "):
            current_file["change_type"] = "renamed"
            continue

        hunk_match = HUNK_HEADER_PATTERN.match(line)

        if hunk_match:
            current_hunk = {
                "old_start": int(hunk_match.group("old_start")),
                "old_count": int(hunk_match.group("old_count") or 1),
                "new_start": int(hunk_match.group("new_start")),
                "new_count": int(hunk_match.group("new_count") or 1),
                "added_lines": [],
                "removed_lines": [],
            }

            current_file["hunks"].append(current_hunk)
            continue

        if current_hunk is None:
            continue

        if line.startswith("+") and not line.startswith("+++"):
            current_hunk["added_lines"].append(line[1:])

        elif line.startswith("-") and not line.startswith("---"):
            current_hunk["removed_lines"].append(line[1:])

    for changed_file in changed_files:
        changed_file.setdefault("change_type", "modified")

    return changed_files


def get_changed_files(
    repository_path: Path,
    base_ref: str = "HEAD~1",
    target_ref: str = "HEAD",
) -> list[dict[str, Any]]:
    """
    Generate and parse the Git diff for a repository.
    """
    diff_text = get_git_diff(
        repository_path=repository_path,
        base_ref=base_ref,
        target_ref=target_ref,
    )

    return parse_git_diff(diff_text)