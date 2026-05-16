import time
from typing import Annotated

import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from jez_face_api.cache import face_template_cache
from jez_face_api.config import settings
from jez_face_api.integrations.laravel import laravel_sync
from jez_face_api.recognition.base import FaceBackend
from jez_face_api.recognition.matching import MatchConfig, match_embedding
from jez_face_api.security import require_internal_token

router = APIRouter(prefix="/api/v1/faces", dependencies=[Depends(require_internal_token)])


class UnavailableBackend:
    def __init__(self, backend_name: str, error: Exception) -> None:
        self.backend_name = backend_name
        self.error = error

    def extract_embedding(self, image_bytes: bytes):
        raise HTTPException(status_code=503, detail=f"{self.backend_name} backend unavailable")

    def extract_embeddings(self, images_bytes: list[bytes]):
        raise HTTPException(status_code=503, detail=f"{self.backend_name} backend unavailable")

    def model_info(self) -> dict:
        return {
            "backend": self.backend_name,
            "loaded": False,
            "error": str(self.error),
        }


_backend: FaceBackend | None = None


def create_backend() -> FaceBackend:
    if settings.FACE_BACKEND != "insightface":
        return UnavailableBackend(
            settings.FACE_BACKEND,
            RuntimeError("Only the InsightFace backend is supported"),
        )
    try:
        from jez_face_api.recognition.insightface_backend import InsightFaceBackend

        return InsightFaceBackend()
    except Exception as exc:
        return UnavailableBackend("insightface", exc)


def get_backend() -> FaceBackend:
    global _backend
    if _backend is None:
        _backend = create_backend()
    return _backend


@router.get("/model-info")
def model_info() -> dict:
    if _backend is None:
        return {
            "backend": settings.FACE_BACKEND,
            "model_name": settings.INSIGHTFACE_MODEL_PACK,
            "det_size": settings.INSIGHTFACE_DET_SIZE,
            "provider": settings.INSIGHTFACE_PROVIDER,
            "loaded": False,
        }
    return _backend.model_info()


@router.get("/status")
def status() -> dict:
    snapshot = face_template_cache.snapshot()
    return {
        "status": "operational",
        "service": "JEZ Face Recognition API",
        "version": "0.1.0",
        "model": model_info().get("model_name", "unknown"),
        "backend": model_info().get("backend", settings.FACE_BACKEND),
        "cached_templates": len(snapshot.user_ids),
        "cache_fingerprint": snapshot.fingerprint,
        "face_threshold": settings.FACE_AUTO_MATCH_THRESHOLD,
    }


@router.post("/reload-cache")
def reload_cache() -> dict:
    users_face_data = laravel_sync.get_users_face_data()
    template_count = sum(len(payload.get("samples", [])) for payload in users_face_data.values())
    if template_count == 0:
        raise HTTPException(
            status_code=503,
            detail="Laravel face data sync returned no templates; existing cache preserved.",
        )

    face_template_cache.reload_from_users_face_data(users_face_data)
    return {
        "status": "success",
        "templates": len(face_template_cache.snapshot().user_ids),
        "users": len(users_face_data),
    }


def _read_upload(upload: UploadFile) -> bytes:
    content = upload.file.read()
    upload.file.close()
    if not content:
        raise HTTPException(status_code=422, detail=f"File {upload.filename or 'image'} kosong")
    return content


@router.post("/register")
def register_faces(
    images: Annotated[list[UploadFile], File()],
    user_id: Annotated[int | None, Form()] = None,
) -> dict:
    start_time = time.time()
    if len(images) < 3 or len(images) > 20:
        raise HTTPException(status_code=422, detail="Minimal 3 foto dan maksimal 20 foto diperlukan")

    backend = get_backend()
    image_bytes = [_read_upload(image) for image in images]
    embeddings = backend.extract_embeddings(image_bytes)
    processing_time = time.time() - start_time
    descriptors = [item.embedding for item in embeddings]

    if len(descriptors) < 3:
        return {
            "status": "error",
            "message": "Tidak cukup wajah terdeteksi. Minimal 3 foto diperlukan.",
            "data": {
                "registered": False,
                "registered_count": len(descriptors),
                "required_count": 3,
                "processing_time": processing_time,
            },
        }

    return {
        "status": "success",
        "message": f"Wajah berhasil didaftar dengan {len(descriptors)} template.",
        "data": {
            "registered": True,
            "descriptor_count": len(descriptors),
            "descriptors": descriptors,
            "model": backend.model_info().get("model_name", "unknown"),
            "processing_time": processing_time,
            "user_id": user_id,
        },
    }


@router.post("/identify")
def identify_face(
    image: Annotated[UploadFile, File()],
    location: Annotated[str | None, Form()] = None,
    metadata: Annotated[str | None, Form()] = None,
    include_user_details: Annotated[bool, Form()] = True,
) -> dict:
    _ = location, metadata
    start_time = time.time()
    backend = get_backend()
    embedding = backend.extract_embedding(_read_upload(image))
    if embedding is None:
        return {"status": "error", "message": "Wajah tidak terdeteksi dalam gambar.", "data": None}

    snapshot = face_template_cache.snapshot()
    if snapshot.matrix.size == 0:
        users_face_data = laravel_sync.get_users_face_data()
        face_template_cache.reload_from_users_face_data(users_face_data)
        snapshot = face_template_cache.snapshot()

    if snapshot.matrix.size == 0:
        return {"status": "not_found", "message": "Tidak ada data wajah terdaftar.", "data": None}

    match_result = match_embedding(
        np.array(embedding.embedding, dtype=np.float32),
        snapshot.matrix,
        snapshot.user_ids,
        MatchConfig(
            auto_match_threshold=settings.FACE_AUTO_MATCH_THRESHOLD,
            ambiguous_threshold=settings.FACE_AMBIGUOUS_THRESHOLD,
            min_margin=settings.FACE_MIN_MARGIN,
        ),
    )
    processing_time = time.time() - start_time

    if match_result.status == "matched" and match_result.user_id is not None:
        user_details = (
            laravel_sync.get_user_details(match_result.user_id)
            if include_user_details
            else {"name": "Unknown", "email": "", "phone": ""}
        )
        return {
            "status": "success",
            "message": "Wajah berhasil dikenali.",
            "data": {
                "user": {
                    "id": match_result.user_id,
                    "name": user_details.get("name", "Unknown"),
                    "email": user_details.get("email", ""),
                    "phone": user_details.get("phone", ""),
                },
                "match": {
                    "score": match_result.best_score,
                    "second_score": match_result.second_score,
                    "margin": match_result.margin,
                    "threshold": settings.FACE_AUTO_MATCH_THRESHOLD,
                },
                "processing_time": processing_time,
                "model": embedding.model,
            },
        }

    return {
        "status": match_result.status,
        "message": "Wajah ambigu. Silakan ulangi scan."
        if match_result.status == "ambiguous"
        else "Wajah tidak dikenali.",
        "data": {
            "best_candidate": match_result.best_candidate,
            "second_candidate": match_result.second_candidate,
            "score": match_result.best_score,
            "second_score": match_result.second_score,
            "margin": match_result.margin,
            "processing_time": processing_time,
        },
    }


@router.post("/quality")
def assess_quality(image: Annotated[UploadFile, File()]) -> dict:
    backend = get_backend()
    embedding = backend.extract_embedding(_read_upload(image))
    if embedding is None:
        return {
            "status": "error",
            "score": 0.0,
            "is_acceptable": False,
            "feedback": "Tidak ada wajah terdeteksi dalam gambar.",
        }

    score = round(min(1.0, embedding.confidence), 2)
    return {
        "status": "good" if score >= 0.8 else "fair",
        "score": score,
        "is_acceptable": score >= 0.7,
        "feedback": "Kualitas wajah baik" if score >= 0.7 else "Kualitas wajah perlu diperbaiki.",
        "details": {"confidence": score, "model": embedding.model},
    }


@router.post("/verify")
def verify_faces(
    image1: Annotated[UploadFile, File()],
    image2: Annotated[UploadFile, File()],
) -> dict:
    backend = get_backend()
    first = backend.extract_embedding(_read_upload(image1))
    second = backend.extract_embedding(_read_upload(image2))
    if first is None or second is None:
        return {"status": "failed", "verified": False, "confidence": 0.0}

    result = match_embedding(
        np.array(first.embedding, dtype=np.float32),
        np.array([second.embedding], dtype=np.float32),
        [1],
        MatchConfig(
            auto_match_threshold=settings.FACE_AUTO_MATCH_THRESHOLD,
            ambiguous_threshold=settings.FACE_AMBIGUOUS_THRESHOLD,
            min_margin=0.0,
        ),
    )
    verified = result.best_score >= settings.FACE_AUTO_MATCH_THRESHOLD
    return {
        "status": "success" if verified else "failed",
        "verified": verified,
        "confidence": result.best_score,
        "distance": 1.0 - result.best_score,
        "threshold": settings.FACE_AUTO_MATCH_THRESHOLD,
        "model": first.model,
    }
