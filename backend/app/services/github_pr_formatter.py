import json
from typing import Any


def _safe_parse_review(
    raw_review: Any,
) -> dict[str, Any]:
    """
    Convert the stored AI review into a dictionary.

    Current CodeSentry incremental results store
    `review` as a JSON string, but this also supports
    a dictionary for future compatibility.
    """
    if isinstance(raw_review, dict):
        return raw_review

    if not isinstance(raw_review, str):
        return {}

    try:
        parsed = json.loads(raw_review)

        if isinstance(parsed, dict):
            return parsed

    except json.JSONDecodeError:
        pass

    return {}


def _format_value(value: Any) -> str:
    """
    Return a readable Markdown-safe fallback value.
    """
    if value is None:
        return "N/A"

    return str(value)


def build_pull_request_comment(
    review_result: dict[str, Any],
) -> str:
    """
    Convert an incremental CodeSentry review result
    into a GitHub Pull Request summary comment.
    """
    repository = review_result.get(
        "repository",
        "Unknown repository",
    )

    risk_score = review_result.get(
        "repository_risk_score"
    )

    risk_band = review_result.get(
        "repository_risk_band",
        "Unknown",
    )

    changed_files_count = review_result.get(
        "changed_files_count",
        0,
    )

    files_reviewed = review_result.get(
        "files_reviewed",
        0,
    )

    files_failed = review_result.get(
        "files_failed",
        0,
    )

    base_ref = review_result.get(
        "base_ref",
        "Unknown",
    )

    target_ref = review_result.get(
        "target_ref",
        "Unknown",
    )

    reviews = review_result.get(
        "reviews",
        [],
    )

    lines = [
        "## CodeSentry AI Code Review",
        "",
        (
            f"Incremental review completed for "
            f"`{repository}`."
        ),
        "",
        "### Review Summary",
        "",
        "| Metric | Result |",
        "|---|---|",
        (
            f"| Repository Risk Score | "
            f"{_format_value(risk_score)} |"
        ),
        (
            f"| Repository Risk Band | "
            f"{_format_value(risk_band)} |"
        ),
        (
            f"| Changed Files | "
            f"{changed_files_count} |"
        ),
        (
            f"| Files Reviewed | "
            f"{files_reviewed} |"
        ),
        (
            f"| Files Failed | "
            f"{files_failed} |"
        ),
        (
            f"| Comparison | "
            f"`{base_ref}` → `{target_ref}` |"
        ),
        "",
    ]

    if not reviews:
        lines.extend([
            "### Findings",
            "",
            (
                "No reviewable changed files or findings "
                "were returned."
            ),
            "",
        ])

        return "\n".join(lines)

    total_findings = 0

    for file_review in reviews:
        file_path = file_review.get(
            "file",
            "Unknown file",
        )

        change_type = file_review.get(
            "change_type",
            "unknown",
        )

        review_scope = file_review.get(
            "review_scope",
            "unknown",
        )

        scoring = file_review.get(
            "scoring",
            {},
        ) or {}

        parsed_review = _safe_parse_review(
            file_review.get("review")
        )

        findings = parsed_review.get(
            "findings",
            [],
        )

        if not isinstance(findings, list):
            findings = []

        total_findings += len(findings)

        summary = (
            parsed_review.get("summary")
            or scoring.get("summary")
            or "No summary available."
        )

        file_risk_score = scoring.get(
            "risk_score"
        )

        file_risk_band = scoring.get(
            "risk_band",
            "Unknown",
        )

        lines.extend([
            f"### `{file_path}`",
            "",
            f"- **Change type:** {change_type}",
            f"- **Review scope:** {review_scope}",
            (
                f"- **Risk:** "
                f"{_format_value(file_risk_score)} "
                f"({_format_value(file_risk_band)})"
            ),
            f"- **Summary:** {summary}",
            "",
        ])

        if findings:
            lines.append("#### Findings")
            lines.append("")

            for index, finding in enumerate(
                findings,
                start=1,
            ):
                if not isinstance(finding, dict):
                    continue

                issue = finding.get(
                    "issue",
                    "Unspecified issue.",
                )

                severity = finding.get(
                    "severity",
                    "Unknown",
                )

                category = finding.get(
                    "category",
                    "general",
                )

                line_number = finding.get(
                    "line",
                )

                location = (
                    f"line {line_number}"
                    if line_number is not None
                    else "line unavailable"
                )

                lines.extend([
                    (
                        f"{index}. **{severity} "
                        f"{category} finding**"
                    ),
                    f"   - {issue}",
                    f"   - Location: `{location}`",
                    "",
                ])

        else:
            lines.extend([
                "#### Findings",
                "",
                "No explicit findings reported.",
                "",
            ])

        best_practices = parsed_review.get(
            "best_practices",
            [],
        )

        if isinstance(best_practices, list) \
                and best_practices:
            lines.append("#### Recommendations")
            lines.append("")

            for recommendation in best_practices:
                lines.append(
                    f"- {recommendation}"
                )

            lines.append("")

    lines.extend([
        "---",
        (
            f"**Total findings:** "
            f"{total_findings}"
        ),
        "",
        (
            "_Generated by CodeSentry "
            "AI Code Reviewer._"
        ),
    ])

    return "\n".join(lines)