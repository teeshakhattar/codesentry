import time

from dotenv import load_dotenv

from app.prompts.review_prompt import REVIEW_PROMPT
from app.services.providers import (
    build_provider_pool,
    ProviderRateLimited,
    ProviderError,
)

load_dotenv()

PROVIDER_POOL = build_provider_pool()
_current_index = 0


def _rotate():
    """
    Move to the next configured AI provider.
    """
    global _current_index

    if not PROVIDER_POOL:
        raise RuntimeError("No AI providers are configured.")

    _current_index = (_current_index + 1) % len(PROVIDER_POOL)


def _call_provider_pool(
    prompt: str,
    max_attempts: int = None,
    request_label: str = "Review",
):
    """
    Send a prompt through the configured provider pool.

    Rate-limit errors rotate to the next provider.
    Other provider errors fail immediately.

    This shared helper keeps full-file review and diff review
    consistent without duplicating retry logic.
    """

    if not PROVIDER_POOL:
        raise RuntimeError("No AI providers are configured.")

    if max_attempts is None:
        # One pass through the provider pool.
        # Avoids long browser requests caused by repeated retry rounds.
        max_attempts = len(PROVIDER_POOL)

    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")

    last_error = None

    for attempt in range(1, max_attempts + 1):
        provider = PROVIDER_POOL[_current_index]

        print(
            f"{request_label} attempt "
            f"{attempt}/{max_attempts} "
            f"using provider: {provider.name}"
        )

        try:
            text = provider.call(prompt)

            print(
                f"\n========== "
                f"{provider.name} {request_label.upper()} RESPONSE "
                f"=========="
            )
            print(text)
            print(
                "=====================================================\n"
            )

            return text

        except ProviderRateLimited as e:
            last_error = e

            print(
                f"{e}\n"
                f"-- rotating to next provider."
            )

            _rotate()

        except ProviderError as e:
            print(
                f"Provider error "
                f"(not rate-limit related): {e}"
            )
            raise

    raise Exception(
        f"All configured provider attempts were exhausted "
        f"after {max_attempts} attempts. "
        f"Last error: {last_error}"
    )


def review_code(
    code: str,
    max_attempts: int = None,
):
    """
    Review complete source-code content.

    Uses the existing CodeSentry review prompt and therefore preserves
    the output contract already expected by scoring_service.py.
    """

    prompt = REVIEW_PROMPT.format(code=code)

    return _call_provider_pool(
        prompt=prompt,
        max_attempts=max_attempts,
        request_label="Full review",
    )


def review_diff(
    file_path: str,
    hunks: list,
    max_attempts: int = None,
):
    """
    Review only changed code extracted from Git diff hunks.

    The diff context is passed through the same REVIEW_PROMPT used by
    full-file review. This keeps incremental-review output aligned with
    the existing ReviewOutput schema and scoring pipeline.
    """

    if not hunks:
        raise ValueError(
            "Cannot review diff because no diff hunks were provided."
        )

    diff_sections = []

    for hunk_index, hunk in enumerate(hunks, start=1):
        added_lines = hunk.get("added_lines", [])
        removed_lines = hunk.get("removed_lines", [])

        old_start = hunk.get("old_start")
        old_count = hunk.get("old_count")
        new_start = hunk.get("new_start")
        new_count = hunk.get("new_count")

        added_text = (
            "\n".join(added_lines)
            if added_lines
            else "(none)"
        )

        removed_text = (
            "\n".join(removed_lines)
            if removed_lines
            else "(none)"
        )

        section = f"""
HUNK {hunk_index}

Old range:
start={old_start}, count={old_count}

New range:
start={new_start}, count={new_count}

ADDED LINES:
{added_text}

REMOVED LINES:
{removed_text}
""".strip()

        diff_sections.append(section)

    diff_context = "\n\n".join(diff_sections)

    incremental_code_context = f"""
INCREMENTAL GIT DIFF REVIEW

File:
{file_path}

Review scope:
Review only the changed code represented below.

Important rules:
- Focus on bugs, security issues, and performance issues introduced by
  or directly exposed by these changes.
- Do not invent issues unrelated to the changed lines.
- Do not review unrelated unchanged code.
- Treat removed lines as previous context.
- Treat added lines as the new code being introduced.
- Return the exact JSON structure required by the CodeSentry review
  instructions.

Git diff hunks:

{diff_context}
""".strip()

    # Important:
    # Reuse REVIEW_PROMPT instead of inventing a second JSON schema.
    # This keeps review_diff compatible with ReviewOutput and
    # scoring_service.py.
    prompt = REVIEW_PROMPT.format(
        code=incremental_code_context
    )

    return _call_provider_pool(
        prompt=prompt,
        max_attempts=max_attempts,
        request_label="Diff review",
    )


def test_gemini():
    """
    Simple provider connectivity test.
    """

    if not PROVIDER_POOL:
        raise RuntimeError("No AI providers are configured.")

    provider = PROVIDER_POOL[_current_index]

    try:
        return provider.call(
            "Reply with exactly these two words: LLM Connected"
        )

    except Exception:
        import traceback

        print(traceback.format_exc())
        raise