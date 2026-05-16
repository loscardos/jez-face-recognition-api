import logging
import shutil
from pathlib import Path

import cv2
import numpy as np

from jez_face_api.config import settings
from jez_face_api.recognition.base import FaceEmbedding

logger = logging.getLogger(__name__)


class InsightFaceBackend:
    def __init__(self) -> None:
        from insightface.app import FaceAnalysis

        self.model_pack = settings.INSIGHTFACE_MODEL_PACK
        self.det_size = settings.INSIGHTFACE_DET_SIZE
        self.provider = settings.INSIGHTFACE_PROVIDER
        try:
            self.app = FaceAnalysis(name=self.model_pack, providers=[self.provider])
        except AssertionError:
            if not self._flatten_nested_model_pack():
                raise
            self.app = FaceAnalysis(name=self.model_pack, providers=[self.provider])
        self.app.prepare(ctx_id=-1, det_size=(self.det_size, self.det_size))

    def extract_embedding(self, image_bytes: bytes) -> FaceEmbedding | None:
        image = self._decode_image(image_bytes)
        if image is None:
            return None

        faces = self.app.get(image)
        if not faces:
            return None

        best_face = max(
            faces,
            key=lambda face: (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1]),
        )
        embedding = best_face.normed_embedding.astype(np.float32).tolist()
        return FaceEmbedding(
            embedding=embedding,
            confidence=float(best_face.det_score),
            model=self.model_pack,
        )

    def extract_embeddings(self, images_bytes: list[bytes]) -> list[FaceEmbedding]:
        results: list[FaceEmbedding] = []
        for image in images_bytes:
            embedding = self.extract_embedding(image)
            if embedding is not None:
                results.append(embedding)
        return results

    def model_info(self) -> dict:
        return {
            "backend": "insightface",
            "model_name": self.model_pack,
            "det_size": self.det_size,
            "provider": self.provider,
            "loaded": True,
        }

    def _flatten_nested_model_pack(self) -> bool:
        model_dir = Path.home() / ".insightface" / "models" / self.model_pack
        nested_dir = model_dir / self.model_pack
        if not nested_dir.is_dir():
            return False

        onnx_files = list(nested_dir.glob("*.onnx"))
        if not onnx_files:
            return False

        logger.warning("Flattening nested InsightFace model directory: %s", nested_dir)
        model_dir.mkdir(parents=True, exist_ok=True)
        for source in onnx_files:
            target = model_dir / source.name
            if not target.exists():
                shutil.move(str(source), str(target))
        try:
            nested_dir.rmdir()
        except OSError:
            pass
        return True

    @staticmethod
    def _decode_image(image_bytes: bytes) -> np.ndarray | None:
        image_array = np.frombuffer(image_bytes, np.uint8)
        return cv2.imdecode(image_array, cv2.IMREAD_COLOR)
