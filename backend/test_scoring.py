from app.services.scoring_service import score_repository

# Real response captured earlier from a live /review-repository run.
# Used here as a fixture so scoring logic can be verified without
# calling the Gemini API at all.
SAMPLE_REVIEWS = [
    {
        "file": "src\\flask\\__main__.py",
        "review": '''```json
{
  "summary": "Concise CLI entry point.",
  "bugs": [],
  "security": [],
  "performance": [],
  "clean_code": ["Clean and readable."],
  "best_practices": ["Consider __name__ guard."],
  "score": 9
}
```'''
    },
    {
        "file": "src\\flask\\blueprints.py",
        "review": '''```json
{
  "summary": "Defines Flask's Blueprint class.",
  "bugs": [
    {"issue": "type: ignore suppresses a return-type warning.", "severity": "Low"}
  ],
  "security": [
    {"issue": "open_resource() may allow path traversal via untrusted input.", "severity": "High"}
  ],
  "performance": [],
  "clean_code": ["Redundant import alias."],
  "best_practices": ["Use safe_join to prevent traversal."],
  "score": 7
}
```'''
    },
    {
        "file": "src\\flask\\views.py",
        "review": '''```json
{
  "summary": "Foundation for class-based views.",
  "bugs": [
    {"issue": "view.view_class referenced before assignment in that branch.", "severity": "Low"}
  ],
  "security": [
    {"issue": "assert used to guard HTTP method dispatch instead of a proper 405.", "severity": "Medium"}
  ],
  "performance": [],
  "clean_code": ["Several type: ignore comments."],
  "best_practices": ["Raise MethodNotAllowed instead of asserting."],
  "score": 8
}
```'''
    },
    {
        "file": "src\\flask\\broken_example.py",
        "review": "Review failed: ClientError('429 RESOURCE_EXHAUSTED...')"
    },
]


def run():
    result = score_repository(SAMPLE_REVIEWS)

    print("=== Repository-level ===")
    print(f"Risk score: {result['repository_risk_score']} ({result['repository_risk_band']})")
    print(f"Files scored: {result['files_scored']} | Files failed: {result['files_failed']}")
    print()

    print("=== Per-file ===")
    for r in result["reviews"]:
        s = r["scoring"]
        print(f"{r['file']}")
        if s["risk_score"] is None:
            print(f"  -> SCORING FAILED: {s['scoring_error']}")
        else:
            print(f"  -> risk_score={s['risk_score']} ({s['risk_band']}), "
                  f"quality_score={s['quality_score']}, findings={s['finding_counts']}")
        print()


if __name__ == "__main__":
    run()