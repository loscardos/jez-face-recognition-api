from fastapi.testclient import TestClient

from jez_face_api.app import create_app
from jez_face_api.cache import FaceTemplateSnapshot
from jez_face_api.config import settings
from jez_face_api.recognition.base import FaceEmbedding


class FakeBackend:
    def __init__(self) -> None:
        self.images: list[bytes] = []

    def extract_embedding(self, image_bytes: bytes):
        self.images.append(image_bytes)
        return FaceEmbedding(embedding=[1.0, 0.0, 0.0], confidence=0.95, model="fake")

    def extract_embeddings(self, images_bytes: list[bytes]):
        self.images.extend(images_bytes)
        return [
            FaceEmbedding(embedding=[1.0, 0.0, 0.0], confidence=0.95, model="fake")
            for _ in images_bytes
        ]

    def model_info(self) -> dict:
        return {"backend": "fake", "model_name": "fake", "loaded": True}


def test_health_endpoint_is_public():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_protected_endpoint_requires_internal_token():
    client = TestClient(create_app())

    response = client.get("/api/v1/faces/model-info")

    assert response.status_code == 401


def test_model_info_accepts_valid_internal_token():
    client = TestClient(create_app())

    response = client.get(
        "/api/v1/faces/model-info",
        headers={"X-Internal-Token": settings.INTERNAL_API_TOKEN},
    )

    assert response.status_code == 200
    assert "backend" in response.json()


def test_status_includes_cache_fingerprint(monkeypatch):
    from jez_face_api.routes import faces

    faces.face_template_cache.reload_from_users_face_data({101: {"samples": [[1.0, 0.0, 0.0]]}})
    client = TestClient(create_app())

    response = client.get(
        "/api/v1/faces/status",
        headers={"X-Internal-Token": settings.INTERNAL_API_TOKEN},
    )

    assert response.status_code == 200
    assert response.json()["cached_templates"] == 1
    assert response.json()["cache_fingerprint"]


def test_reload_cache_rejects_empty_laravel_sync_without_clearing_existing_cache(monkeypatch):
    from jez_face_api.routes import faces

    faces.face_template_cache.reload_from_users_face_data({101: {"samples": [[1.0, 0.0, 0.0]]}})
    monkeypatch.setattr(faces.laravel_sync, "get_users_face_data", lambda: {})
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/faces/reload-cache",
        headers={"X-Internal-Token": settings.INTERNAL_API_TOKEN},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Laravel face data sync returned no templates; existing cache preserved."
    snapshot = faces.face_template_cache.snapshot()
    assert snapshot.matrix.shape == (1, 3)
    assert snapshot.user_ids == [101]


def test_reload_cache_accepts_non_empty_laravel_sync(monkeypatch):
    from jez_face_api.routes import faces

    faces.face_template_cache.reload_from_users_face_data({})
    monkeypatch.setattr(
        faces.laravel_sync,
        "get_users_face_data",
        lambda: {202: {"samples": [[0.0, 1.0, 0.0], [0.0, 0.9, 0.1]]}},
    )
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/faces/reload-cache",
        headers={"X-Internal-Token": settings.INTERNAL_API_TOKEN},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["templates"] == 2


def test_identify_accepts_multipart_image_and_rejects_json(monkeypatch):
    from jez_face_api.routes import faces

    fake_backend = FakeBackend()
    monkeypatch.setattr(faces, "get_backend", lambda: fake_backend)
    monkeypatch.setattr(
        faces.face_template_cache,
        "snapshot",
        lambda: FaceTemplateSnapshot(
            matrix=faces.np.array([[1.0, 0.0, 0.0]], dtype=faces.np.float32),
            user_ids=[101],
        ),
    )
    monkeypatch.setattr(
        faces.laravel_sync,
        "get_user_details",
        lambda user_id: {"name": "Tester", "email": "tester@example.test", "phone": ""},
    )
    client = TestClient(create_app())
    headers = {"X-Internal-Token": settings.INTERNAL_API_TOKEN}

    json_response = client.post(
        "/api/v1/faces/identify",
        headers=headers,
        json={"image": "data:image/jpeg;base64,abc"},
    )
    multipart_response = client.post(
        "/api/v1/faces/identify",
        headers=headers,
        files={"image": ("face.jpg", b"fake-image-bytes", "image/jpeg")},
        data={"metadata": '{"device":"mobile"}'},
    )

    assert json_response.status_code == 422
    assert multipart_response.status_code == 200
    assert multipart_response.json()["status"] == "success"
    assert fake_backend.images == [b"fake-image-bytes"]


def test_register_accepts_multiple_multipart_images(monkeypatch):
    from jez_face_api.routes import faces

    fake_backend = FakeBackend()
    monkeypatch.setattr(faces, "get_backend", lambda: fake_backend)
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/faces/register",
        headers={"X-Internal-Token": settings.INTERNAL_API_TOKEN},
        data={"user_id": "101"},
        files=[
            ("images", ("face1.jpg", b"first", "image/jpeg")),
            ("images", ("face2.jpg", b"second", "image/jpeg")),
            ("images", ("face3.jpg", b"third", "image/jpeg")),
        ],
    )

    assert response.status_code == 200
    assert response.json()["data"]["descriptor_count"] == 3
    assert fake_backend.images == [b"first", b"second", b"third"]
