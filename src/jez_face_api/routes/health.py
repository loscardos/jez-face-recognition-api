from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "face_recognition",
        "version": "0.1.0",
    }

