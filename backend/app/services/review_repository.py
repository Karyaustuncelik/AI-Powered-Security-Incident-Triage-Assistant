# Bu dosya incident review durumunu SQLite içinde kalıcı tutar.

from contextlib import closing
import sqlite3
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from app.models.domain import IncidentReview


DB_PATH = Path(__file__).resolve().parents[2] / "data" / "triage_assistant.db"


class ReviewRepository:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or DB_PATH
        self._initialize()

    def _initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS incident_reviews (
                    incident_id TEXT PRIMARY KEY,
                    review_status TEXT NOT NULL,
                    assigned_analyst TEXT,
                    review_notes TEXT,
                    reviewed_at TEXT
                )
                """
            )
            connection.commit()

    def get_review(self, incident_id: str) -> IncidentReview | None:
        with closing(sqlite3.connect(self.db_path)) as connection:
            row = connection.execute(
                """
                SELECT incident_id, review_status, assigned_analyst, review_notes, reviewed_at
                FROM incident_reviews
                WHERE incident_id = ?
                """,
                (incident_id,),
            ).fetchone()

        if row is None:
            return None

        reviewed_at = datetime.fromisoformat(row[4]) if row[4] else None
        return IncidentReview(
            incident_id=row[0],
            review_status=row[1],
            assigned_analyst=row[2],
            review_notes=row[3],
            reviewed_at=reviewed_at,
        )

    def save_review(self, review: IncidentReview) -> IncidentReview:
        reviewed_at = review.reviewed_at or datetime.now(UTC)

        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.execute(
                """
                INSERT INTO incident_reviews (
                    incident_id,
                    review_status,
                    assigned_analyst,
                    review_notes,
                    reviewed_at
                )
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(incident_id) DO UPDATE SET
                    review_status = excluded.review_status,
                    assigned_analyst = excluded.assigned_analyst,
                    review_notes = excluded.review_notes,
                    reviewed_at = excluded.reviewed_at
                """,
                (
                    review.incident_id,
                    review.review_status.value,
                    review.assigned_analyst,
                    review.review_notes,
                    reviewed_at.isoformat(),
                ),
            )
            connection.commit()

        return IncidentReview(
            incident_id=review.incident_id,
            review_status=review.review_status,
            assigned_analyst=review.assigned_analyst,
            review_notes=review.review_notes,
            reviewed_at=reviewed_at,
        )


@lru_cache
def get_review_repository() -> ReviewRepository:
    return ReviewRepository()
