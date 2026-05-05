# Bu dosya kullanıcının yüklediği log session'larını yerelde JSON olarak saklar.

import json
import re
from pathlib import Path

from app.models.domain import UploadSession


UPLOADS_DIR = Path(__file__).resolve().parents[2] / "data" / "uploads"


class UploadSessionRepository:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or UPLOADS_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_session(
        self,
        session: UploadSession,
        original_bytes: bytes | None = None,
    ) -> UploadSession:
        session_path = self._session_path(session.upload_id)
        session_path.write_text(
            json.dumps(session.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        if original_bytes is not None:
            original_path = self._original_path(session.upload_id, session.filename)
            original_path.write_bytes(original_bytes)

        return session

    def get_session(self, upload_id: str) -> UploadSession | None:
        session_path = self._session_path(upload_id)
        if not session_path.exists():
            return None

        payload = json.loads(session_path.read_text(encoding="utf-8"))
        return UploadSession.model_validate(payload)

    def _session_path(self, upload_id: str) -> Path:
        return self.base_dir / f"{upload_id}.json"

    def _original_path(self, upload_id: str, filename: str) -> Path:
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", filename)
        return self.base_dir / f"{upload_id}_{safe_name}"
