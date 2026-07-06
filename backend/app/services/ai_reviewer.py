import time

from dotenv import load_dotenv

from app.prompts.review_prompt import REVIEW_PROMPT
from app.services.providers import build_provider_pool, ProviderRateLimited, ProviderError

load_dotenv()

PROVIDER_POOL = build_provider_pool()
_current_index = 0


def _rotate():
    global _current_index
    _current_index = (_current_index + 1) % len(PROVIDER_POOL)


def review_code(code: str, max_attempts: int = None):
    """
    Sends the code to whichever provider is currently active in the
    pool. On a rate-limit error, rotates to the next provider and
    retries immediately -- since each provider has its own separate
    quota, there's no need to wait. Only pauses briefly once every
    provider in the pool has been tried in this call.
    """
    prompt = REVIEW_PROMPT.format(code=code)

    if max_attempts is None:
        # One full pass through the pool, plus a second pass in case
        # a rate limit clears quickly (e.g. per-minute limits).
        max_attempts = len(PROVIDER_POOL) * 2

    last_error = None

    for attempt in range(1, max_attempts + 1):
        provider = PROVIDER_POOL[_current_index]
        print(f"Attempt {attempt}/{max_attempts} using provider: {provider.name}")

        try:
            text = provider.call(prompt)

            print(f"\n========== {provider.name} RESPONSE ==========")
            print(text)
            print("================================================\n")

            return text

        except ProviderRateLimited as e:
            last_error = e
            print(f"{e}\n-- rotating to next provider.")
            _rotate()

            if attempt % len(PROVIDER_POOL) == 0:
                wait_seconds = 5
                print(f"All providers tried this round. Waiting {wait_seconds}s before next pass...")
                time.sleep(wait_seconds)

        except ProviderError as e:
            # Not a rate limit -- e.g. malformed request, server error
            # unrelated to quota. Don't burn through the whole pool
            # retrying something that will fail the same way every time.
            print(f"Provider error (not rate-limit related): {e}")
            raise

    raise Exception(
        f"All {len(PROVIDER_POOL)} providers exhausted after {max_attempts} attempts. "
        f"Last error: {last_error}"
    )


def test_gemini():
    provider = PROVIDER_POOL[_current_index]
    try:
        return provider.call("Reply with exactly these two words: LLM Connected")
    except Exception:
        import traceback
        print(traceback.format_exc())
        raise