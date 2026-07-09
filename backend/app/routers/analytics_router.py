from fastapi import APIRouter

from app.services.database_service import (
    get_analytics_summary,
    get_repositories_summary,
    get_repository_analytics,
)


router = APIRouter(
    prefix="/analytics",
    tags=["Analytics"],
)


@router.get("")
def get_analytics():
    analytics = get_analytics_summary()
    repositories = get_repositories_summary()

    by_band = analytics.get(
        "by_band",
        {},
    )

    average_risk_score = analytics.get(
        "average_risk_score"
    )

    return {
        "total_scans": analytics.get(
            "total_scans",
            0,
        ),
        "repositories_reviewed": len(
            repositories
        ),
        "average_risk_score": (
            average_risk_score
            if average_risk_score is not None
            else 0
        ),
        "high_risk_scans": by_band.get(
            "High",
            0,
        ),
        "risk_distribution": {
            "High": by_band.get("High", 0),
            "Medium": by_band.get("Medium", 0),
            "Low": by_band.get("Low", 0),
            "Unknown": (
                by_band.get("Unknown", 0)
                + by_band.get(None, 0)
            ),
        },
        "risk_trend": analytics.get(
            "trend",
            [],
        ),
    }


@router.get("/repositories/{repository_name}")
def get_repository_analytics_view(
    repository_name: str,
):
    analytics = get_repository_analytics(
        repository_name
    )

    by_band = analytics.get(
        "by_band",
        {},
    )

    average_risk_score = analytics.get(
        "average_risk_score"
    )

    return {
        "repository": repository_name,
        "total_scans": analytics.get(
            "total_scans",
            0,
        ),
        "average_risk_score": (
            average_risk_score
            if average_risk_score is not None
            else 0
        ),
        "high_risk_scans": by_band.get(
            "High",
            0,
        ),
        "risk_distribution": {
            "High": by_band.get("High", 0),
            "Medium": by_band.get("Medium", 0),
            "Low": by_band.get("Low", 0),
            "Unknown": (
                by_band.get("Unknown", 0)
                + by_band.get(None, 0)
            ),
        },
        "risk_trend": analytics.get(
            "trend",
            [],
        ),
    }