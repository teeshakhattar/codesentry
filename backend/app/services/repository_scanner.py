from pathlib import Path

IGNORE_DIRECTORIES = {
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "env",
    ".env",
    "docs",
    "tests",
    "examples",
    "example",
    "dist",
    "build",
    "node_modules",
    ".idea",
    ".vscode"
}

SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".java",
    ".cpp",
    ".c",
    ".cs",
    ".go",
    ".php",
    ".rb",
    ".rs",
    ".swift",
    ".kt",
    ".scala"
}

# Filenames that are boilerplate / auto-generated / low review value.
# Matched as exact filenames (case-insensitive).
IGNORE_FILENAMES = {
    "__init__.py",
    "setup.py",
    "conftest.py",
    "manage.py",
    "wsgi.py",
    "asgi.py",
}

# Filename substrings to skip (test files, migrations, configs, minified).
IGNORE_FILENAME_PATTERNS = (
    "test_",     # test_something.py
    "_test",     # something_test.py / something_test.js
    ".test",     # something.test.js / something.test.ts
    ".spec",     # something.spec.js
    ".config",   # webpack.config.js, jest.config.js
    ".min",      # foo.min.js
    ".d.ts",     # type declaration files
)

# Hard safety cap so a huge repo can never exceed API quota in one run.
# Set to None to disable.
MAX_FILES = 8


def _is_ignored_filename(filename: str) -> bool:
    name_lower = filename.lower()

    if name_lower in IGNORE_FILENAMES:
        return True

    if any(pattern in name_lower for pattern in IGNORE_FILENAME_PATTERNS):
        return True

    return False


def scan_repository(repository_path: Path) -> list[str]:
    """
    Recursively scans a repository and returns core source code files,
    excluding vendored/generated/test/boilerplate files so that AI review
    calls are spent on files that matter (and stay within API rate limits).
    """

    if not repository_path.exists():
        raise FileNotFoundError(
            f"Repository not found: {repository_path}"
        )

    files = []

    for path in repository_path.rglob("*"):

        if not path.is_file():
            continue

        if any(part in IGNORE_DIRECTORIES for part in path.parts):
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        if _is_ignored_filename(path.name):
            continue

        files.append(path)

    # Prefer smaller, shallower files first (usually more "core logic"
    # than huge generated/vendored files further down the tree).
    files.sort(key=lambda p: (len(p.parts), p.stat().st_size))

    if MAX_FILES is not None:
        files = files[:MAX_FILES]

    return sorted(str(p.resolve()) for p in files)