from fastapi import Header, HTTPException, status

from jez_face_api.config import settings


def require_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    if x_internal_token != settings.INTERNAL_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal service token",
        )

