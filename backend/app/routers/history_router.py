from fastapi import APIRouter, HTTPException

from app.services.database_service import (
    list_scans,
    get_scan,
    get_repositories_summary,
    get_repository_detail,
    get_repository_scans,
    get_analytics_summary,
)

router = APIRouter()


@router.get("/scans")
def get_scans():
    """Returns lightweight metadata for every past scan, most recent first."""
    return {"scans": list_scans()}


@router.get("/scans/{scan_id}")
def get_scan_detail(scan_id: int):
    """Returns the full stored result for one past scan."""
    scan = get_scan(scan_id)

    if not scan:
        raise HTTPException(
            status_code=404,
            detail=f"Scan {scan_id} not found"
        )

    return scan


@router.get("/repositories")
def get_repositories():
    """Returns one entry per unique repository."""
    return {
        "repositories": get_repositories_summary()
    }


@router.get("/repositories/{repository_name}")
def get_repository(repository_name: str):
    """Returns summary details for one repository."""
    repository = get_repository_detail(repository_name)

    if not repository:
        raise HTTPException(
            status_code=404,
            detail=f"Repository '{repository_name}' not found"
        )

    return repository


@router.get("/repositories/{repository_name}/scans")
def get_repository_scan_history(repository_name: str):
    """Returns scan history for one specific repository."""
    scans = get_repository_scans(repository_name)

    return {
        "repository": repository_name,
        "scan_count": len(scans),
        "scans": scans
    }


@router.get("/analytics")
def get_analytics():
    """Returns aggregate statistics across all scans."""
    return get_analytics_summary()