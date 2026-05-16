from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class FaceEmbedding:
    embedding: list[float]
    confidence: float
    model: str


class FaceBackend(Protocol):
    def extract_embedding(self, image_bytes: bytes) -> FaceEmbedding | None:
        ...

    def extract_embeddings(self, images_bytes: list[bytes]) -> list[FaceEmbedding]:
        ...

    def model_info(self) -> dict:
        ...
