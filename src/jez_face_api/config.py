import os
from dataclasses import dataclass
from functools import cached_property

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LARAVEL_API_URL: str = os.getenv("LARAVEL_API_URL", "http://localhost:8000/api")
    LARAVEL_API_TOKEN: str = os.getenv("LARAVEL_API_TOKEN", "")
    INTERNAL_API_TOKEN: str = os.getenv("INTERNAL_API_TOKEN", "change-this-in-production")
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    FACE_BACKEND: str = os.getenv("FACE_BACKEND", "insightface")
    MIN_DETECTION_CONFIDENCE: float = float(os.getenv("MIN_DETECTION_CONFIDENCE", "0.8"))
    INSIGHTFACE_MODEL_PACK: str = os.getenv("INSIGHTFACE_MODEL_PACK", "buffalo_m")
    INSIGHTFACE_DET_SIZE: int = int(os.getenv("INSIGHTFACE_DET_SIZE", "640"))
    INSIGHTFACE_PROVIDER: str = os.getenv("INSIGHTFACE_PROVIDER", "CPUExecutionProvider")
    FACE_AUTO_MATCH_THRESHOLD: float = float(os.getenv("FACE_AUTO_MATCH_THRESHOLD", "0.45"))
    FACE_AMBIGUOUS_THRESHOLD: float = float(os.getenv("FACE_AMBIGUOUS_THRESHOLD", "0.38"))
    FACE_MIN_MARGIN: float = float(os.getenv("FACE_MIN_MARGIN", "0.05"))

    @cached_property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]


settings = Settings()
