import json
import re

from pydantic import ValidationError

from app.schemas.review_output_schema import ReviewOutput


# --- Severity weighting -----------------------------------------------
# Design rationale (viva-ready): a single High severity issue should
# outweigh several Low ones, since High issues carry disproportionate
# real-world risk compared to style nits.
SEVERITY_WEIGHTS = {
    "High": 5,
    "Medium": 3,
    "Low": 1,
}

# Scale applied to the raw weighted sum before capping at 100.
RISK_SCALE = 4

RISK_BANDS = [
    (33, "Low"),
    (66, "Medium"),
    (100, "High"),
]


def _risk_band(
    score: float,
    counts: dict | None = None,
) -> str:
    """
    Convert numeric risk into a human-readable band.

    A High-severity finding creates a severity floor so one serious
    issue cannot be hidden by an otherwise low aggregate score.
    """
    if counts and counts.get("High", 0) > 0:
        return "High" if score >= 50 else "Medium"

    for threshold, label in RISK_BANDS:
        if score <= threshold:
            return label

    return "High"


def extract_review_json(
    review_text: str,
) -> ReviewOutput | None:
    """
    Parse AI review JSON and validate it against ReviewOutput.

    Markdown-fence handling is retained as a fallback for providers
    that do not fully honor JSON-only response mode.
    """
    if not review_text or not isinstance(review_text, str):
        return None

    match = re.search(
        r"```(?:json)?\s*(\{.*\})\s*```",
        review_text,
        re.DOTALL,
    )

    json_str = (
        match.group(1)
        if match
        else review_text.strip()
    )

    try:
        raw = json.loads(json_str)

    except (json.JSONDecodeError, TypeError):
        return None

    try:
        return ReviewOutput.model_validate(raw)

    except ValidationError:
        return None


def score_file(
    review_text: str,
) -> dict:
    """
    Compute risk scoring for one AI review JSON string.
    """
    parsed = extract_review_json(review_text)

    if parsed is None:
        return {
            "risk_score": None,
            "risk_band": "Unknown",
            "quality_score": None,
            "finding_counts": {
                "High": 0,
                "Medium": 0,
                "Low": 0,
            },
            "category_counts": {
                "bug": 0,
                "security": 0,
                "performance": 0,
            },
            "scoring_error": (
                "Could not parse or validate review "
                "output for scoring."
            ),
        }

    counts = {
        "High": 0,
        "Medium": 0,
        "Low": 0,
    }

    category_counts = {
        "bug": 0,
        "security": 0,
        "performance": 0,
    }

    raw_weighted = 0

    for finding in parsed.findings:
        severity = finding.severity.value
        category = finding.category.value

        counts[severity] += 1
        category_counts[category] += 1

        raw_weighted += SEVERITY_WEIGHTS[
            severity
        ]

    risk_score = min(
        100,
        raw_weighted * RISK_SCALE,
    )

    return {
        "risk_score": risk_score,
        "risk_band": _risk_band(
            risk_score,
            counts,
        ),
        "quality_score": parsed.score,
        "finding_counts": counts,
        "category_counts": category_counts,
        "summary": parsed.summary,
    }


def score_function_reviews(
    function_reviews: list,
) -> dict:
    """
    Aggregate multiple function-level AI reviews into one file-level
    scoring result.

    Each function is scored independently first. Valid function scores
    are then aggregated for the containing file.

    Risk uses the mean function risk so files with more changed
    functions are not automatically penalized purely because of size.

    Finding counts are summed because they represent actual detected
    issues across all affected functions.

    Quality score uses the mean of valid function quality scores.
    """
    function_scoring = []

    valid_risk_scores = []
    valid_quality_scores = []

    total_findings = {
        "High": 0,
        "Medium": 0,
        "Low": 0,
    }

    total_categories = {
        "bug": 0,
        "security": 0,
        "performance": 0,
    }

    summaries = []

    for function_entry in function_reviews:
        review_text = function_entry.get(
            "review"
        )

        scoring = score_file(review_text)

        function_scoring.append(
            {
                "name": function_entry.get(
                    "name"
                ),
                "start_line": function_entry.get(
                    "start_line"
                ),
                "end_line": function_entry.get(
                    "end_line"
                ),
                "is_async": function_entry.get(
                    "is_async",
                    False,
                ),
                "scoring": scoring,
            }
        )

        risk_score = scoring.get(
            "risk_score"
        )

        if risk_score is None:
            continue

        valid_risk_scores.append(
            risk_score
        )

        quality_score = scoring.get(
            "quality_score"
        )

        if quality_score is not None:
            valid_quality_scores.append(
                quality_score
            )

        for severity in total_findings:
            total_findings[severity] += (
                scoring["finding_counts"].get(
                    severity,
                    0,
                )
            )

        for category in total_categories:
            total_categories[category] += (
                scoring["category_counts"].get(
                    category,
                    0,
                )
            )

        summary = scoring.get("summary")

        if summary:
            summaries.append(summary)

    if not valid_risk_scores:
        return {
            "risk_score": None,
            "risk_band": "Unknown",
            "quality_score": None,
            "finding_counts": total_findings,
            "category_counts": total_categories,
            "functions_scored": 0,
            "functions_failed": len(
                function_reviews
            ),
            "function_scoring": (
                function_scoring
            ),
            "scoring_error": (
                "Could not parse or validate any "
                "function review output for scoring."
            ),
        }

    file_risk_score = round(
        sum(valid_risk_scores)
        / len(valid_risk_scores),
        1,
    )

    if valid_quality_scores:
        file_quality_score = round(
            sum(valid_quality_scores)
            / len(valid_quality_scores),
            1,
        )
    else:
        file_quality_score = None

    return {
        "risk_score": file_risk_score,
        "risk_band": _risk_band(
            file_risk_score,
            total_findings,
        ),
        "quality_score": file_quality_score,
        "finding_counts": total_findings,
        "category_counts": total_categories,
        "functions_scored": len(
            valid_risk_scores
        ),
        "functions_failed": (
            len(function_reviews)
            - len(valid_risk_scores)
        ),
        "function_scoring": function_scoring,
        "summary": (
            summaries[0]
            if len(summaries) == 1
            else (
                f"{len(summaries)} affected "
                f"functions reviewed."
            )
        ),
    }


def score_repository(
    reviews: list,
) -> dict:
    """
    Score full-file, diff-fallback, and AST function-level reviews.

    Supported shapes:

    Traditional review:
        "review": "<AI JSON string>"

    AST review:
        "review": [
            {
                "name": "...",
                "review": "<AI JSON string>"
            }
        ]
    """
    scored_reviews = []
    valid_scores = []

    for entry in reviews:
        review_data = entry.get("review")

        if isinstance(review_data, list):
            scoring = score_function_reviews(
                review_data
            )
        else:
            scoring = score_file(
                review_data
            )

        scored_entry = {
            **entry,
            "scoring": scoring,
        }

        scored_reviews.append(
            scored_entry
        )

        if scoring["risk_score"] is not None:
            valid_scores.append(
                scoring["risk_score"]
            )

    if valid_scores:
        repo_risk_score = round(
            sum(valid_scores)
            / len(valid_scores),
            1,
        )
    else:
        repo_risk_score = None

    repo_has_high = any(
        review["scoring"][
            "finding_counts"
        ].get("High", 0) > 0
        for review in scored_reviews
        if review["scoring"][
            "risk_score"
        ] is not None
    )

    return {
        "reviews": scored_reviews,
        "repository_risk_score": (
            repo_risk_score
        ),
        "repository_risk_band": (
            _risk_band(
                repo_risk_score,
                {
                    "High": (
                        1
                        if repo_has_high
                        else 0
                    )
                },
            )
            if repo_risk_score is not None
            else "Unknown"
        ),
        "files_scored": len(
            valid_scores
        ),
        "files_failed": (
            len(reviews)
            - len(valid_scores)
        ),
    }