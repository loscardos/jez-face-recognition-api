from fastapi import HTTPException

from jez_face_api.config import Settings
from jez_face_api.security import require_internal_token


def test_settings_parses_cors_origins():
    settings = Settings(CORS_ORIGINS="http://localhost:3000,http://localhost:5173")

    assert settings.cors_origins == ["http://localhost:3000", "http://localhost:5173"]


def test_internal_token_defaults_to_non_empty_development_value():
    settings = Settings()

    assert settings.INTERNAL_API_TOKEN


def test_security_dependency_rejects_missing_token():
    try:
        require_internal_token(None)
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("Expected missing token to be rejected")

