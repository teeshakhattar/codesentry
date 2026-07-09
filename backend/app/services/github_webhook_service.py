import hashlib
import hmac
import os

from dotenv import load_dotenv


load_dotenv()


GITHUB_WEBHOOK_SECRET = os.getenv(
    "GITHUB_WEBHOOK_SECRET"
)


def verify_github_signature(
    payload_body: bytes,
    signature_header: str | None,
) -> bool:
    """
    Verify a GitHub webhook request using
    the X-Hub-Signature-256 header.
    """

    if not GITHUB_WEBHOOK_SECRET:
        raise RuntimeError(
            "GITHUB_WEBHOOK_SECRET is not configured."
        )

    if not signature_header:
        return False

    expected_signature = (
        "sha256="
        + hmac.new(
            GITHUB_WEBHOOK_SECRET.encode("utf-8"),
            payload_body,
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(
        expected_signature,
        signature_header,
    )