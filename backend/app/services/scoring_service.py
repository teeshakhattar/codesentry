import json
import re

from pydantic import ValidationError

from app.schemas.review_output_schema import ReviewOutput

# --- Severity weighting -----------------------------------------------
# Design rationale (viva-ready): a single High severity issue should
# outweigh several Low ones, since High issues (e.g. path traversal)
# carry disproportionate real-world risk compared to style nits.
SEVERITY_WEIGHTS = {
    "High": 5,
    "Medium": 3,
    "Low": 1,
}

# Scale applied to the raw weighted sum before capping at 100.
# Chosen so a "genuinely bad" file (e.g. 2 High + 2 Medium + 2 Low
# = 10 + 6 + 2 = 18 raw) lands around 70-75/100 -- clearly risky,
# but not automatically maxed out by one bad file.
RISK_SCALE = 4

RISK_BANDS = [
    (33, "Low"),
    (66, "Medium"),
    (100, "High"),
]


def _risk_band(score: float, counts: dict = None) -> str:
    # Severity floor: a single High-severity finding should never let a
    # file's overall band read as "Low", even if the weighted score is
    # small. This prevents one serious issue (e.g. a security bug) from
    # being diluted by an otherwise-clean file.
    if counts and counts.get("High", 0) > 0:
        return "High" if score >= 50 else "Medium"

    for threshold, label in RISK_BANDS:
        if score <= threshold:
            return label
    return "High"


def extract_review_json(review_text: str) -> ReviewOutput | None:
    """
    The AI reviewer returns text that's usually already valid JSON now
    that providers run in JSON mode -- but the markdown-fence fallback
    is kept for any provider/response that doesn't honor it.

    This now does two things where it used to do one: parses the text,
    AND validates it against ReviewOutput. A response that parses as
    JSON but doesn't match the contract (wrong severity string, missing
    field, wrong type) is treated the same as unparseable -- returns
    None so callers degrade gracefully, rather than silently scoring
    against fields that don't mean what we assume they mean.
    """
    if not review_text or not isinstance(review_text, str):
        return None

    match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", review_text, re.DOTALL)
    json_str = match.group(1) if match else review_text.strip()

    try:
        raw = json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return None

    try:
        return ReviewOutput.model_validate(raw)
    except ValidationError:
        return None


def score_file(review_text: str) -> dict:
    """
    Computes a risk score (0-100, higher = riskier) for a single file's
    review, plus a risk band and a breakdown of the findings that fed it.
    """
    parsed = extract_review_json(review_text)

    if parsed is None:
        return {
            "risk_score": None,
            "risk_band": "Unknown",
            "quality_score": None,
            "finding_counts": {"High": 0, "Medium": 0, "Low": 0},
            "category_counts": {"bug": 0, "security": 0, "performance": 0},
            "scoring_error": "Could not parse or validate review output for scoring.",
        }

    counts = {"High": 0, "Medium": 0, "Low": 0}
    category_counts = {"bug": 0, "security": 0, "performance": 0}
    raw_weighted = 0

    for finding in parsed.findings:
        severity = finding.severity.value
        counts[severity] += 1
        category_counts[finding.category.value] += 1
        raw_weighted += SEVERITY_WEIGHTS[severity]

    risk_score = min(100, raw_weighted * RISK_SCALE)

    return {
        "risk_score": risk_score,
        "risk_band": _risk_band(risk_score, counts),
        "quality_score": parsed.score,
        "finding_counts": counts,
        "category_counts": category_counts,
        "summary": parsed.summary,
    }


def score_repository(reviews: list) -> dict:
    """
    Takes the existing `reviews` list (each: {"file": ..., "review": ...})
    and returns each entry enriched with its scoring breakdown, plus a
    repository-level aggregate risk score and band.
    """
    scored_reviews = []
    valid_scores = []

    for entry in reviews:
        scoring = score_file(entry["review"])
        scored_reviews.append({
            **entry,
            "scoring": scoring,
        })
        if scoring["risk_score"] is not None:
            valid_scores.append(scoring["risk_score"])

    if valid_scores:
        repo_risk_score = round(sum(valid_scores) / len(valid_scores), 1)
    else:
        repo_risk_score = None

    # If any single file in the repo has a High-severity finding, the
    # repository-level band should reflect that too -- an averaged score
    # across many clean files shouldn't bury one seriously risky file.
    repo_has_high = any(
        r["scoring"]["finding_counts"].get("High", 0) > 0
        for r in scored_reviews
        if r["scoring"]["risk_score"] is not None
    )

    return {
        "reviews": scored_reviews,
        "repository_risk_score": repo_risk_score,
        "repository_risk_band": (
            _risk_band(repo_risk_score, {"High": 1 if repo_has_high else 0})
            if repo_risk_score is not None else "Unknown"
        ),
        "files_scored": len(valid_scores),
        "files_failed": len(reviews) - len(valid_scores),
    }