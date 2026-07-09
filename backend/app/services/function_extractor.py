import ast
from pathlib import Path
from typing import Any


SUPPORTED_PYTHON_EXTENSIONS = {".py"}


def extract_functions_from_code(
    code: str,
) -> list[dict[str, Any]]:
    """
    Extract function and method boundaries from Python source code.

    Uses Python's built-in AST, so this is deterministic and does not
    depend on the AI provider.
    """
    if not code or not code.strip():
        return []

    try:
        tree = ast.parse(code)
    except SyntaxError:
        return []

    functions = []

    for node in ast.walk(tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ):
            functions.append(
                {
                    "name": node.name,
                    "start_line": node.lineno,
                    "end_line": getattr(
                        node,
                        "end_lineno",
                        node.lineno,
                    ),
                    "is_async": isinstance(
                        node,
                        ast.AsyncFunctionDef,
                    ),
                }
            )

    functions.sort(
        key=lambda item: (
            item["start_line"],
            item["end_line"],
        )
    )

    return functions


def get_changed_line_numbers(
    hunks: list[dict[str, Any]],
) -> set[int]:
    """
    Convert Git diff hunk metadata into changed line numbers
    on the new version of the file.
    """
    changed_lines = set()

    for hunk in hunks:
        new_start = hunk.get("new_start")
        new_count = hunk.get("new_count", 1)

        if new_start is None:
            continue

        if new_count is None:
            new_count = 1

        for line_number in range(
            new_start,
            new_start + new_count,
        ):
            changed_lines.add(line_number)

    return changed_lines


def find_changed_functions(
    code: str,
    hunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Return only functions whose source ranges overlap
    changed lines from Git diff hunks.
    """
    functions = extract_functions_from_code(code)
    changed_lines = get_changed_line_numbers(hunks)

    if not functions or not changed_lines:
        return []

    affected_functions = []

    for function in functions:
        start_line = function["start_line"]
        end_line = function["end_line"]

        overlaps_change = any(
            start_line <= line_number <= end_line
            for line_number in changed_lines
        )

        if overlaps_change:
            affected_functions.append(function)

    return affected_functions


def extract_function_source(
    code: str,
    function: dict[str, Any],
) -> str:
    """
    Extract exact source text for one function.
    """
    lines = code.splitlines()

    start_index = max(
        function["start_line"] - 1,
        0,
    )

    end_index = function["end_line"]

    return "\n".join(
        lines[start_index:end_index]
    )


def get_changed_functions_for_file(
    file_path: Path,
    hunks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Read a Python file and return affected functions
    with their exact source code.
    """
    if file_path.suffix.lower() not in SUPPORTED_PYTHON_EXTENSIONS:
        return []

    if not file_path.exists():
        return []

    try:
        code = file_path.read_text(
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return []

    changed_functions = find_changed_functions(
        code=code,
        hunks=hunks,
    )

    results = []

    for function in changed_functions:
        results.append(
            {
                **function,
                "source": extract_function_source(
                    code,
                    function,
                ),
            }
        )

    return results