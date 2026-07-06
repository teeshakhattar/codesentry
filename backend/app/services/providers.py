import os

from openai import OpenAI
from openai import RateLimitError as OpenAIRateLimitError
from openai import APIStatusError as OpenAIAPIStatusError

from google import genai
from google.genai import types as genai_types
from google.genai.errors import ClientError as GeminiClientError
from google.genai.errors import ServerError as GeminiServerError

from app.schemas.review_output_schema import ReviewOutput


class ProviderRateLimited(Exception):
    """Raised when a provider hits a rate limit or quota error.
    The caller should rotate to the next provider and retry."""
    pass


class ProviderError(Exception):
    """Raised for any other provider-side failure that isn't a
    rate limit -- the caller should NOT retry blindly on these."""
    pass


class OpenAICompatibleProvider:
    """
    Wraps any provider that speaks the OpenAI chat-completions API
    shape -- this covers Groq and DeepSeek without needing separate
    client code for each.
    """

    def __init__(self, name: str, api_key: str, base_url: str, model: str):
        self.name = name
        self.model = model
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def call(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                # JSON mode: guarantees syntactically valid JSON, not a
                # specific schema -- Pydantic validation downstream is
                # still what enforces the actual contract. Both Groq and
                # DeepSeek require the literal word "JSON" to appear
                # somewhere in the prompt for this mode to activate,
                # which REVIEW_PROMPT already satisfies.
                response_format={"type": "json_object"},
            )
            text = response.choices[0].message.content
            if not text:
                raise ProviderError(f"{self.name} returned no text.")
            return text

        except OpenAIRateLimitError as e:
            raise ProviderRateLimited(f"{self.name} rate-limited: {e}")
        except OpenAIAPIStatusError as e:
            raise ProviderError(f"{self.name} API error: {e}")


class GeminiProvider:
    """
    Wraps Gemini's own SDK, since it doesn't speak the OpenAI-compatible
    shape. Normalizes its errors to the same ProviderRateLimited /
    ProviderError types so the reviewer doesn't need to know which
    provider it's currently talking to.
    """

    def __init__(self, name: str, api_key: str, model: str):
        self.name = name
        self.model = model
        self.client = genai.Client(api_key=api_key)

    def call(self, prompt: str) -> str:
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_mime_type="application/json",
                    # Gemini is the one provider that can actually enforce
                    # the schema at the API level, not just "valid JSON".
                    # If your installed google-genai version doesn't accept
                    # a Pydantic class here, drop this line -- the shared
                    # ReviewOutput.model_validate() call in scoring_service
                    # still catches malformed output either way.
                    response_schema=ReviewOutput,
                ),
            )
            if hasattr(response, "text") and response.text:
                return response.text
            raise ProviderError(f"{self.name} returned no text.")

        except GeminiClientError as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                raise ProviderRateLimited(f"{self.name} rate-limited: {e}")
            raise ProviderError(f"{self.name} client error: {e}")

        except GeminiServerError as e:
            # 503-style overload -- treat as retryable via rotation
            # rather than a hard failure.
            raise ProviderRateLimited(f"{self.name} server overloaded: {e}")


def build_provider_pool() -> list:
    """
    Builds the rotation pool from whichever provider keys are present
    in .env. Order matters: providers are tried in this order, and the
    pool rotates forward on rate limits. Groq is listed first since its
    free-tier limits are the most generous; Gemini last since it has
    the most restrictive daily cap of the three.
    """
    providers = []

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        providers.append(OpenAICompatibleProvider(
            name="Groq",
            api_key=groq_key,
            base_url="https://api.groq.com/openai/v1",
            model="llama-3.1-8b-instant",
        ))

    deepseek_key = os.getenv("DEEPSEEK_API_KEY")
    if deepseek_key:
        providers.append(OpenAICompatibleProvider(
            name="DeepSeek",
            api_key=deepseek_key,
            base_url="https://api.deepseek.com",
            model="deepseek-chat",
        ))

    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        providers.append(GeminiProvider(
            name="Gemini",
            api_key=gemini_key,
            model="gemini-2.5-flash",
        ))

    if not providers:
        raise Exception(
            "No provider keys found. Set at least one of GROQ_API_KEY, "
            "DEEPSEEK_API_KEY, GEMINI_API_KEY in your .env file."
        )

    return providers