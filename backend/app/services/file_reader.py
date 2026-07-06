from pathlib import Path


def read_repository_files(file_paths: list[str]) -> list[dict]:
    """
    Reads the contents of all supported source code files.

    Returns:
        [
            {
                "file": "...",
                "content": "..."
            }
        ]
    """

    files = []

    for file_path in file_paths:

        path = Path(file_path)

        if not path.exists():
            continue

        try:
            content = path.read_text(
                encoding="utf-8",
                errors="ignore"
            )

            files.append(
                {
                    "file": str(path.resolve()),
                    "content": content
                }
            )

        except Exception as e:
            print(f"Could not read {path}: {e}")

    return files