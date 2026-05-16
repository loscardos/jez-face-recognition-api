from dataclasses import dataclass
from threading import RLock

import numpy as np


@dataclass(frozen=True)
class FaceTemplateSnapshot:
    matrix: np.ndarray
    user_ids: list[int]


class FaceTemplateCache:
    def __init__(self) -> None:
        self._lock = RLock()
        self._matrix = np.empty((0, 0), dtype=np.float32)
        self._user_ids: list[int] = []

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
        with self._lock:
            self._matrix = matrix
            self._user_ids = user_ids

    def snapshot(self) -> FaceTemplateSnapshot:
        with self._lock:
            return FaceTemplateSnapshot(matrix=self._matrix.copy(), user_ids=list(self._user_ids))


face_template_cache = FaceTemplateCache()

