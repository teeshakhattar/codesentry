import hashlib
import hmac
import json
import urllib.error
import urllib.request


WEBHOOK_URL = (
    "http://127.0.0.1:8000/webhooks/github"
)

SECRET = "codesentry-dev-secret-2026"


payload = {
    "action": "opened",
    "number": 7,
    "repository": {
        "full_name": (
            "teeshakhattar/codesentry-ast-test"
        ),
        "clone_url": (
            "https://github.com/"
            "teeshakhattar/"
            "codesentry-ast-test.git"
        ),
    },
    "pull_request": {
        "base": {
            "sha": "929435d",
        },
        "head": {
            "sha": "d6fc9c1",
        },
    },
}


payload_body = json.dumps(
    payload,
    separators=(",", ":"),
).encode("utf-8")


signature = (
    "sha256="
    + hmac.new(
        SECRET.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()
)


request = urllib.request.Request(
    WEBHOOK_URL,
    data=payload_body,
    method="POST",
    headers={
        "Content-Type": "application/json",
        "X-GitHub-Event": "pull_request",
        "X-GitHub-Delivery": (
            "signature-test-001"
        ),
        "X-Hub-Signature-256": signature,
    },
)


try:
    with urllib.request.urlopen(
        request,
        timeout=120,
    ) as response:
        print(
            "STATUS:",
            response.status,
        )

        print(
            response.read().decode("utf-8")
        )

except urllib.error.HTTPError as exc:
    print(
        "STATUS:",
        exc.code,
    )

    print(
        exc.read().decode("utf-8")
    )