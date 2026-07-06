import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone

# Database file lives at the project root, alongside backend/ and frontend/.
DB_PATH = Path(__file__).resolve().parent.parent.parent / "codesentry.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates the scans table if it doesn't already exist. Safe to call
    on every app startup."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            repository TEXT NOT NULL,
            repo_url TEXT,
            scanned_at TEXT NOT NULL,
            files_reviewed INTEGER,
            files_scored INTEGER,
            files_failed INTEGER,
            repository_risk_score REAL,
            repository_risk_band TEXT,
            result_json TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def save_scan(repo_url: str, result: dict) -> int:
    """Stores a completed review_repository() result and returns its new scan id."""
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO scans (repository, repo_url, scanned_at, files_reviewed, files_scored,
                            files_failed, repository_risk_score, repository_risk_band, result_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result.get("repository"),
            repo_url,
            datetime.now(timezone.utc).isoformat(),
            result.get("files_reviewed"),
            result.get("files_scored"),
            result.get("files_failed"),
            result.get("repository_risk_score"),
            result.get("repository_risk_band"),
            json.dumps(result),
        ),
    )
    conn.commit()
    scan_id = cursor.lastrowid
    conn.close()
    return scan_id


def list_scans(limit: int = 100):
    """Returns lightweight metadata for past scans, most recent first."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT id, repository, repo_url, scanned_at, files_reviewed, files_scored,
               files_failed, repository_risk_score, repository_risk_band
        FROM scans
        ORDER BY scanned_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_scan(scan_id: int):
    """Returns the full stored result (including all file reviews) for one scan,
    or None if it doesn't exist."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM scans WHERE id = ?", (scan_id,)).fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    data["result"] = json.loads(data.pop("result_json"))
    return data


def get_repositories_summary():
    """One row per unique repository, showing its most recent scan plus how
    many times it's been scanned in total."""
    conn = get_connection()
    rows = conn.execute(
        """
        SELECT s.repository, s.repo_url, s.scanned_at as last_scanned_at,
               s.repository_risk_score, s.repository_risk_band, s.files_reviewed,
               (SELECT COUNT(*) FROM scans s2 WHERE s2.repository = s.repository) as scan_count
        FROM scans s
        WHERE s.scanned_at = (
            SELECT MAX(s3.scanned_at) FROM scans s3 WHERE s3.repository = s.repository
        )
        ORDER BY last_scanned_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
def get_repository_detail(repository_name: str):
    """Returns the latest repository summary for one repository."""

    conn = get_connection()

    row = conn.execute(
        """
        SELECT
            s.repository,
            s.repo_url,
            s.scanned_at AS last_scanned_at,
            s.repository_risk_score,
            s.repository_risk_band,
            s.files_reviewed,
            (
                SELECT COUNT(*)
                FROM scans s2
                WHERE s2.repository = s.repository
            ) AS scan_count
        FROM scans s
        WHERE s.repository = ?
        ORDER BY s.scanned_at DESC
        LIMIT 1
        """,
        (repository_name,)
    ).fetchone()

    conn.close()

    if not row:
        return None

    return dict(row)
def get_repository_scans(repository_name: str):
    """Return all scans for one repository, newest first."""

    conn = get_connection()

    rows = conn.execute(
        """
        SELECT
            id,
            repository,
            repo_url,
            scanned_at,
            repository_risk_score,
            repository_risk_band,
            files_reviewed
        FROM scans
        WHERE repository = ?
        ORDER BY scanned_at DESC
        """,
        (repository_name,)
    ).fetchall()

    conn.close()

    return [dict(row) for row in rows]

def get_analytics_summary():
    """Aggregate stats across every scan ever run: totals, average risk,
    breakdown by risk band, and a chronological trend for charting."""
    conn = get_connection()
    total_scans = conn.execute("SELECT COUNT(*) as c FROM scans").fetchone()["c"]
    avg_risk = conn.execute("SELECT AVG(repository_risk_score) as a FROM scans").fetchone()["a"]
    by_band_rows = conn.execute(
        "SELECT repository_risk_band, COUNT(*) as c FROM scans GROUP BY repository_risk_band"
    ).fetchall()
    trend_rows = conn.execute(
        """
        SELECT id, repository, scanned_at, repository_risk_score
        FROM scans ORDER BY scanned_at ASC
        """
    ).fetchall()
    conn.close()

    return {
        "total_scans": total_scans,
        "average_risk_score": round(avg_risk, 1) if avg_risk is not None else None,
        "by_band": {row["repository_risk_band"]: row["c"] for row in by_band_rows},
        "trend": [dict(row) for row in trend_rows],
    }