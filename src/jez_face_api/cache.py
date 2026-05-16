from dataclasses import dataclass
import hashlib
import json
from threading import RLock

import numpy as np


@dataclass(frozen=True)
class FaceTemplateSnapshot:
    matrix: np.ndarray
    user_ids: list[int]
    fingerprint: str = ""


class FaceTemplateCache:
    def __init__(self) -> None:
        self._lock = RLock()
        self._matrix = np.empty((0, 0), dtype=np.float32)
        self._user_ids: list[int] = []
        self._fingerprint = ""

    def reload_from_users_face_data(self, users_face_data: dict[int, dict]) -> None:
        embeddings: list[list[float]] = []
        user_ids: list[int] = []
        for user_id, payload in users_face_data.items():
            for sample in payload.get("samples", []):
                embeddings.append(sample)
                user_ids.append(int(user_id))

        matrix = (
            np.array(embeddings, dtype=np.float32)
            if embeddings
            else np.empty((0, 0), dtype=np.float32)
        )
        fingerprint_payload = [
            [user_id, [round(float(value), 8) for value in embedding]]
            for user_id, embedding in zip(user_ids, embeddings)
        ]
        fingerprint = hashlib.sha256(
            json.dumps(fingerprint_payload, separators=(",", ":")).encode("utf-8")
        ).hexdigest() if fingerprint_payload else ""
        with self._lock:
            self._matrix = matrix
            self._user_ids = user_ids
            self._fingerprint = fingerprint

    def snapshot(self) -> FaceTemplateSnapshot:
        with self._lock:
            return FaceTemplateSnapshot(
                matrix=self._matrix.copy(),
                user_ids=list(self._user_ids),
                fingerprint=self._fingerprint,
            )


face_template_cache = FaceTemplateCache()

