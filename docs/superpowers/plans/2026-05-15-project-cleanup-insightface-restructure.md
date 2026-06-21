# Project Cleanup And InsightFace Restructure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean the repository documentation/scripts, restructure the FastAPI service into a maintainable package, and prepare the production path from the current DeepFace flow to an InsightFace cached matching service.

**Architecture:** Keep Laravel as the public business API and make this project a private face identity service. Move runtime code into `src/jez_face_api`, isolate configuration, models, integrations, recognition backends, cache, and routes, and keep root files minimal. Replace scattered historical docs with a small docs set that describes the current architecture, operations, API, and migration plan.

**Tech Stack:** Python 3.10+, FastAPI, Pydantic, NumPy, pytest, httpx/TestClient, DeepFace compatibility during transition, InsightFace + ONNXRuntime for the target recognition backend, shell scripts under `scripts/`.

---

## Current Problems To Fix

- Root directory has historical `.md` files with conflicting claims: older docs mention OpenCV/Haar/face-recognition, newer code uses DeepFace.
- `start.sh`, `start_server.sh`, and `setup.sh` hard-code `/home/royyan/projects/face-attendance-ai`, which is wrong for this workspace.
- `test_api.sh` calls endpoints that do not exist in `main.py`, including `/api/status` and `/api/faces/sync`.
- Runtime code sits in root-level files, making it hard to test or swap recognition backends.
- Identification fetches all Laravel face data every request and parses JSON repeatedly.
- Static temp files under `/tmp` can collide under concurrent requests.
- FastAPI CORS is open to all origins and the service has no internal token guard.

## Target File Structure

```text
.
├── README.md
├── Dockerfile
├── requirements.txt
├── pyproject.toml
├── .env.example
├── main.py
├── scripts/
│   ├── setup.sh
│   ├── start.sh
│   └── smoke_test.sh
├── src/
│   └── jez_face_api/
│       ├── __init__.py
│       ├── app.py
│       ├── config.py
│       ├── security.py
│       ├── schemas.py
│       ├── routes/
│       │   ├── __init__.py
│       │   ├── health.py
│       │   └── faces.py
│       ├── integrations/
│       │   ├── __init__.py
│       │   └── laravel.py
│       ├── recognition/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── deepface_backend.py
│       │   ├── insightface_backend.py
│       │   └── matching.py
│       └── cache.py
├── tests/
│   ├── test_matching.py
│   ├── test_security.py
│   └── test_api_contract.py
└── docs/
    ├── architecture.md
    ├── api.md
    ├── operations.md
    ├── migration-insightface.md
    ├── improvements.md
    ├── archive/
    │   ├── DATABASE_CONFIG.md
    │   ├── FACE_REGISTRATION_DOCUMENTATION.md
    │   ├── IMPLEMENTATION_DEEPFACE.md
    │   ├── IMPLEMENTATION_GUIDE.md
    │   ├── INTEGRATION_GUIDE.md
    │   ├── REGISTRATION_WORKFLOW.md
    │   ├── SETUP_COMPLETE.md
    │   └── WORKFLOW_COMPLETE_SUMMARY.md
    └── superpowers/
        └── plans/
            └── 2026-05-15-project-cleanup-insightface-restructure.md
```

## Documentation Cleanup Policy

- `README.md`: current quick start, current endpoints, current architecture summary.
- `docs/architecture.md`: Laravel/FastAPI/database boundaries and production deployment shape.
- `docs/api.md`: exact FastAPI request/response contracts.
- `docs/operations.md`: setup, start, Docker, smoke test, environment variables.
- `docs/migration-insightface.md`: staged migration from DeepFace embeddings to InsightFace `buffalo_m`.
- `docs/improvements.md`: keep as analysis/spec, lightly update only if it conflicts with implementation reality.
- `docs/archive/*.md`: move old historical docs here without deleting their information.

---

### Task 1: Add Packaging And Test Baseline

**Files:**
- Create: `pyproject.toml`
- Create: `.env.example`
- Create: `tests/test_matching.py`
- Modify: `requirements.txt`

- [ ] **Step 1: Create Python project metadata**

Create `pyproject.toml`:

```toml
[project]
name = "jez-face-recognition-api"
version = "0.1.0"
description = "Private FastAPI face identity service for JEZ attendance"
requires-python = ">=3.10"

[tool.pytest.ini_options]
pythonpath = ["src", "."]
testpaths = ["tests"]
addopts = "-q"

[tool.ruff]
line-length = 100
target-version = "py310"
```

- [ ] **Step 2: Add a real environment template**

Create `.env.example`:

```env
HOST=127.0.0.1
PORT=8000
DEBUG=false

LARAVEL_API_URL=http://localhost:8000/api
LARAVEL_API_TOKEN=
INTERNAL_API_TOKEN=change-this-in-production
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

FACE_BACKEND=deepface
DEEPFACE_MODEL=Facenet
DEEPFACE_DETECTOR=opencv
FACE_MATCH_THRESHOLD=0.65
MIN_DETECTION_CONFIDENCE=0.8

INSIGHTFACE_MODEL_PACK=buffalo_m
INSIGHTFACE_DET_SIZE=640
INSIGHTFACE_PROVIDER=CPUExecutionProvider

FACE_AUTO_MATCH_THRESHOLD=0.45
FACE_AMBIGUOUS_THRESHOLD=0.38
FACE_MIN_MARGIN=0.05
```

- [ ] **Step 3: Add test dependencies**

Modify `requirements.txt` by appending:

```text

# Testing and local quality
pytest>=8.0.0
httpx>=0.27.0
ruff>=0.6.0
```

- [ ] **Step 4: Write the first failing matching test**

Create `tests/test_matching.py`:

```python
import numpy as np

from jez_face_api.recognition.matching import MatchConfig, match_embedding


def test_match_embedding_accepts_clear_top_candidate():
    matrix = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.6, 0.8, 0.0],
            [0.0, 1.0, 0.0],
        ],
        dtype=np.float32,
    )
    user_ids = [101, 202, 303]
    query = np.array([1.0, 0.0, 0.0], dtype=np.float32)

    result = match_embedding(
        query,
        matrix,
        user_ids,
        MatchConfig(auto_match_threshold=0.45, ambiguous_threshold=0.38, min_margin=0.05),
    )

    assert result.status == "matched"
    assert result.user_id == 101
    assert result.best_score == 1.0
    assert result.second_score == 0.6
    assert result.margin == 0.4


def test_match_embedding_marks_small_margin_as_ambiguous():
    matrix = np.array(
        [
            [1.0, 0.0],
            [0.99, 0.01],
        ],
        dtype=np.float32,
    )
    user_ids = [101, 202]
    query = np.array([1.0, 0.0], dtype=np.float32)

    result = match_embedding(
        query,
        matrix,
        user_ids,
        MatchConfig(auto_match_threshold=0.45, ambiguous_threshold=0.38, min_margin=0.05),
    )

    assert result.status == "ambiguous"
    assert result.user_id is None
    assert result.best_candidate == 101
    assert result.second_candidate == 202
```

- [ ] **Step 5: Run the test to verify it fails**

Run:

```bash
pytest tests/test_matching.py -q
```

Expected: fail with `ModuleNotFoundError: No module named 'jez_face_api'`.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .env.example requirements.txt tests/test_matching.py
git commit -m "test: add project baseline and matching contract"
```

---

### Task 2: Create Package Skeleton And Vector Matching

**Files:**
- Create: `src/jez_face_api/__init__.py`
- Create: `src/jez_face_api/recognition/__init__.py`
- Create: `src/jez_face_api/recognition/matching.py`
- Test: `tests/test_matching.py`

- [ ] **Step 1: Create package markers**

Create `src/jez_face_api/__init__.py`:

```python
__all__ = ["__version__"]

__version__ = "0.1.0"
```

Create `src/jez_face_api/recognition/__init__.py`:

```python
from jez_face_api.recognition.matching import MatchConfig, MatchResult, match_embedding

__all__ = ["MatchConfig", "MatchResult", "match_embedding"]
```

- [ ] **Step 2: Implement vectorized matching**

Create `src/jez_face_api/recognition/matching.py`:

```python
from dataclasses import dataclass
from typing import Sequence

import numpy as np


@dataclass(frozen=True)
class MatchConfig:
    auto_match_threshold: float
    ambiguous_threshold: float
    min_margin: float


@dataclass(frozen=True)
class MatchResult:
    status: str
    user_id: int | None
    best_candidate: int | None
    second_candidate: int | None
    best_score: float
    second_score: float
    margin: float


def _normalize(vector: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vector))
    if norm == 0.0:
        return vector.astype(np.float32)
    return (vector / norm).astype(np.float32)


def match_embedding(
    query_embedding: np.ndarray,
    template_matrix: np.ndarray,
    user_ids: Sequence[int],
    config: MatchConfig,
) -> MatchResult:
    if template_matrix.size == 0 or len(user_ids) == 0:
        return MatchResult("not_found", None, None, None, 0.0, 0.0, 0.0)

    if template_matrix.shape[0] != len(user_ids):
        raise ValueError("template_matrix rows must match user_ids length")

    query = _normalize(query_embedding)
    matrix = np.apply_along_axis(_normalize, 1, template_matrix.astype(np.float32))
    scores = matrix @ query
    order = np.argsort(scores)[::-1]

    best_index = int(order[0])
    second_index = int(order[1]) if len(order) > 1 else best_index
    best_score = float(scores[best_index])
    second_score = float(scores[second_index]) if len(order) > 1 else 0.0
    margin = best_score - second_score
    best_candidate = int(user_ids[best_index])
    second_candidate = int(user_ids[second_index]) if len(order) > 1 else None

    if best_score >= config.auto_match_threshold and margin >= config.min_margin:
        status = "matched"
        user_id = best_candidate
    elif best_score >= config.ambiguous_threshold:
        status = "ambiguous"
        user_id = None
    else:
        status = "not_found"
        user_id = None

    return MatchResult(
        status=status,
        user_id=user_id,
        best_candidate=best_candidate,
        second_candidate=second_candidate,
        best_score=round(best_score, 6),
        second_score=round(second_score, 6),
        margin=round(margin, 6),
    )
```

- [ ] **Step 3: Run matching tests**

Run:

```bash
pytest tests/test_matching.py -q
```

Expected: `2 passed`.

- [ ] **Step 4: Commit**

```bash
git add src/jez_face_api tests/test_matching.py
git commit -m "feat: add vectorized face matching"
```

---

### Task 3: Move Configuration Into The Package

**Files:**
- Create: `src/jez_face_api/config.py`
- Modify: `config.py`
- Test: `tests/test_security.py`

- [ ] **Step 1: Write config tests**

Create `tests/test_security.py`:

```python
from jez_face_api.config import Settings


def test_settings_parses_cors_origins():
    settings = Settings(CORS_ORIGINS="http://localhost:3000,http://localhost:5173")

    assert settings.cors_origins == ["http://localhost:3000", "http://localhost:5173"]


def test_internal_token_defaults_to_non_empty_development_value():
    settings = Settings()

    assert settings.INTERNAL_API_TOKEN
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
pytest tests/test_security.py -q
```

Expected: fail with `ModuleNotFoundError` or `ImportError` for `jez_face_api.config`.

- [ ] **Step 3: Implement packaged settings**

Create `src/jez_face_api/config.py`:

```python
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
    FACE_BACKEND: str = os.getenv("FACE_BACKEND", "deepface")
    DEEPFACE_MODEL: str = os.getenv("DEEPFACE_MODEL", "Facenet")
    DEEPFACE_DETECTOR: str = os.getenv("DEEPFACE_DETECTOR", "opencv")
    FACE_MATCH_THRESHOLD: float = float(os.getenv("FACE_MATCH_THRESHOLD", "0.65"))
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
```

- [ ] **Step 4: Keep root `config.py` as a compatibility shim**

Replace root `config.py` with:

```python
from jez_face_api.config import Settings, settings


class Config:
    HOST = settings.HOST
    PORT = settings.PORT
    DEBUG = settings.DEBUG
    LARAVEL_API_URL = settings.LARAVEL_API_URL
    DEEPFACE_MODEL = settings.DEEPFACE_MODEL
    DEEPFACE_DETECTOR = settings.DEEPFACE_DETECTOR
    FACE_MATCH_THRESHOLD = settings.FACE_MATCH_THRESHOLD
    MIN_DETECTION_CONFIDENCE = settings.MIN_DETECTION_CONFIDENCE


config = Config()
```

- [ ] **Step 5: Run config tests**

Run:

```bash
pytest tests/test_security.py -q
```

Expected: `2 passed`.

- [ ] **Step 6: Commit**

```bash
git add src/jez_face_api/config.py config.py tests/test_security.py
git commit -m "refactor: move configuration into package"
```

---

### Task 4: Replace Root Shell Scripts With Clean `scripts/`

**Files:**
- Create: `scripts/setup.sh`
- Create: `scripts/start.sh`
- Create: `scripts/smoke_test.sh`
- Delete: `setup.sh`
- Delete: `start.sh`
- Delete: `start_server.sh`
- Delete: `test_api.sh`
- Modify: `README.md`

- [ ] **Step 1: Create portable setup script**

Create `scripts/setup.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"

echo "Setting up JEZ Face Recognition API in $ROOT_DIR"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python executable '$PYTHON_BIN' was not found" >&2
  exit 1
fi

if [ ! -d "$VENV_DIR" ]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt

if [ ! -f ".env" ] && [ -f ".env.example" ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
fi

mkdir -p logs face_data
echo "Setup complete"
```

- [ ] **Step 2: Create portable start script**

Create `scripts/start.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

VENV_DIR="${VENV_DIR:-.venv}"

if [ -d "$VENV_DIR" ]; then
  source "$VENV_DIR/bin/activate"
fi

export PYTHONPATH="${ROOT_DIR}/src:${PYTHONPATH:-}"
exec python -m uvicorn jez_face_api.app:create_app --factory --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}"
```

- [ ] **Step 3: Create smoke test script aligned with real endpoints**

Create `scripts/smoke_test.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

API_URL="${1:-http://127.0.0.1:8000}"

echo "Health:"
curl -fsS "$API_URL/health" | python -m json.tool

echo "Model info:"
curl -fsS "$API_URL/api/v1/faces/model-info" | python -m json.tool
```

- [ ] **Step 4: Make scripts executable**

Run:

```bash
chmod +x scripts/setup.sh scripts/start.sh scripts/smoke_test.sh
```

Expected: command exits with status `0`.

- [ ] **Step 5: Remove stale root scripts**

Run:

```bash
rm setup.sh start.sh start_server.sh test_api.sh
```

Expected: root no longer contains `.sh` files.

- [ ] **Step 6: Commit**

```bash
git add scripts README.md
git rm setup.sh start.sh start_server.sh test_api.sh
git commit -m "chore: replace stale root scripts with portable scripts"
```

---

### Task 5: Archive Historical Markdown And Create Current Docs

**Files:**
- Create: `docs/archive/`
- Create: `docs/architecture.md`
- Create: `docs/api.md`
- Create: `docs/operations.md`
- Create: `docs/migration-insightface.md`
- Modify: `README.md`
- Move: root historical Markdown files into `docs/archive/`

- [ ] **Step 1: Move historical docs to archive**

Run:

```bash
mkdir -p docs/archive
mv DATABASE_CONFIG.md docs/archive/DATABASE_CONFIG.md
mv FACE_REGISTRATION_DOCUMENTATION.md docs/archive/FACE_REGISTRATION_DOCUMENTATION.md
mv IMPLEMENTATION_DEEPFACE.md docs/archive/IMPLEMENTATION_DEEPFACE.md
mv IMPLEMENTATION_GUIDE.md docs/archive/IMPLEMENTATION_GUIDE.md
mv INTEGRATION_GUIDE.md docs/archive/INTEGRATION_GUIDE.md
mv REGISTRATION_WORKFLOW.md docs/archive/REGISTRATION_WORKFLOW.md
mv SETUP_COMPLETE.md docs/archive/SETUP_COMPLETE.md
mv WORKFLOW_COMPLETE_SUMMARY.md docs/archive/WORKFLOW_COMPLETE_SUMMARY.md
```

Expected: only `README.md` remains as a root Markdown file.

- [ ] **Step 2: Replace README with concise current entrypoint**

Replace `README.md`:

```markdown
# JEZ Face Recognition API

Private FastAPI service for JEZ attendance face identity checks.

## Current Status

The current runtime supports the existing DeepFace-compatible API while the project is being migrated toward InsightFace `buffalo_m`, cached embeddings, and vectorized matching.

## Quick Start

```bash
scripts/setup.sh
scripts/start.sh
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

## Main Endpoints

- `GET /health`
- `POST /api/v1/faces/register`
- `POST /api/v1/faces/identify`
- `POST /api/v1/faces/quality`
- `POST /api/v1/faces/verify`
- `GET /api/v1/faces/status`
- `GET /api/v1/faces/model-info`

## Documentation

- `docs/architecture.md`
- `docs/api.md`
- `docs/operations.md`
- `docs/improvements.md`
- `docs/migration-insightface.md`
- `docs/archive/`
```

- [ ] **Step 3: Create architecture doc**

Create `docs/architecture.md`:

```markdown
# Architecture

Laravel remains the public API and attendance business-rule owner. This FastAPI service is private/internal and only performs face detection, embedding generation, template matching, and match audit reporting.

## Request Flow

```text
Mobile/Web Attendance
  -> Laravel API
  -> FastAPI Face Identity Service
  -> cached face template matrix
  -> Laravel attendance decision and storage
```

## Production Rules

- Bind FastAPI to `127.0.0.1`, a Docker internal network, or a private subnet.
- Require `X-Internal-Token` for non-health endpoints.
- Do not expose this service directly to the public internet.
- Store embeddings in `user_face_templates`, not `users.u_face`, after InsightFace migration.
```

- [ ] **Step 4: Create API doc**

Create `docs/api.md`:

```markdown
# API

## `GET /health`

Returns service health and active backend metadata.

## `POST /api/v1/faces/register`

Registers 3 to 20 face samples for compatibility with the existing Laravel integration.

```json
{
  "images": ["data:image/jpeg;base64,..."],
  "user_id": 123
}
```

## `POST /api/v1/faces/identify`

Identifies one face image.

```json
{
  "image": "data:image/jpeg;base64,...",
  "location": {"lat": -6.2, "lng": 106.8},
  "metadata": {"device": "mobile"}
}
```

## `POST /api/v1/faces/quality`

Checks whether an image is usable for enrollment.

## `POST /api/v1/faces/verify`

Compares two face images.
```

- [ ] **Step 5: Create operations doc**

Create `docs/operations.md`:

```markdown
# Operations

## Setup

```bash
scripts/setup.sh
```

## Start

```bash
scripts/start.sh
```

## Smoke Test

```bash
scripts/smoke_test.sh http://127.0.0.1:8000
```

## Environment

Use `.env.example` as the source of truth for supported environment variables.
```

- [ ] **Step 6: Create migration doc**

Create `docs/migration-insightface.md`:

```markdown
# InsightFace Migration

## Target

Use InsightFace `buffalo_m` with ONNXRuntime CPU provider, cached template matrix, top-2 margin checks, and Laravel-owned business decisions.

## Required Migration Rules

- Re-enroll all active users after switching to InsightFace.
- Do not compare old DeepFace embeddings with InsightFace embeddings.
- Calibrate `FACE_AUTO_MATCH_THRESHOLD`, `FACE_AMBIGUOUS_THRESHOLD`, and `FACE_MIN_MARGIN` against real JEZ employee data.
- Keep DeepFace compatibility only until Laravel and mobile clients are migrated.

## Target Tables

```sql
CREATE TABLE user_face_templates (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    detector_name VARCHAR(50) NULL,
    embedding JSON NOT NULL,
    quality_score DECIMAL(5,2) NULL,
    sample_index INT DEFAULT 1,
    is_active TINYINT DEFAULT 1,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL
);
```
```

- [ ] **Step 7: Commit**

```bash
git add README.md docs
git commit -m "docs: consolidate current documentation"
```

---

### Task 6: Introduce App Factory, Schemas, And Security Guard

**Files:**
- Create: `src/jez_face_api/app.py`
- Create: `src/jez_face_api/security.py`
- Create: `src/jez_face_api/schemas.py`
- Create: `src/jez_face_api/routes/__init__.py`
- Create: `src/jez_face_api/routes/health.py`
- Modify: `main.py`
- Test: `tests/test_api_contract.py`
- Test: `tests/test_security.py`

- [ ] **Step 1: Write API contract tests**

Create `tests/test_api_contract.py`:

```python
from fastapi.testclient import TestClient

from jez_face_api.app import create_app


def test_health_endpoint_is_public():
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_protected_endpoint_requires_internal_token():
    client = TestClient(create_app())

    response = client.get("/api/v1/faces/model-info")

    assert response.status_code == 401
```

- [ ] **Step 2: Implement security dependency**

Create `src/jez_face_api/security.py`:

```python
from fastapi import Header, HTTPException, status

from jez_face_api.config import settings


def require_internal_token(x_internal_token: str | None = Header(default=None)) -> None:
    if x_internal_token != settings.INTERNAL_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid internal service token",
        )
```

- [ ] **Step 3: Implement schemas**

Create `src/jez_face_api/schemas.py`:

```python
from typing import Any

from pydantic import BaseModel


class RegisterRequest(BaseModel):
    images: list[str]
    user_id: int | None = None


class IdentifyRequest(BaseModel):
    image: str
    location: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class QualityRequest(BaseModel):
    image: str


class VerifyRequest(BaseModel):
    image1: str
    image2: str
```

- [ ] **Step 4: Implement health route**

Create `src/jez_face_api/routes/__init__.py`:

```python
__all__: list[str] = []
```

Create `src/jez_face_api/routes/health.py`:

```python
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {
        "status": "healthy",
        "service": "face_recognition",
        "version": "0.1.0",
    }
```

- [ ] **Step 5: Implement app factory with protected placeholder route**

Create `src/jez_face_api/app.py`:

```python
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jez_face_api.config import settings
from jez_face_api.routes.health import router as health_router
from jez_face_api.security import require_internal_token


def create_app() -> FastAPI:
    app = FastAPI(
        title="JEZ Face Recognition API",
        description="Private face identity service for JEZ attendance",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)

    @app.get("/api/v1/faces/model-info", dependencies=[Depends(require_internal_token)])
    def model_info() -> dict[str, str]:
        return {"backend": settings.FACE_BACKEND}

    return app


app = create_app()
```

- [ ] **Step 6: Replace root app entrypoint**

Replace `main.py`:

```python
import uvicorn

from jez_face_api.app import create_app
from jez_face_api.config import settings

app = create_app()


if __name__ == "__main__":
    uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level="info")
```

- [ ] **Step 7: Run tests**

Run:

```bash
pytest tests/test_api_contract.py tests/test_security.py -q
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add main.py src/jez_face_api tests
git commit -m "refactor: add FastAPI app factory and internal token guard"
```

---

### Task 7: Move Laravel Integration Into Package

**Files:**
- Create: `src/jez_face_api/integrations/__init__.py`
- Create: `src/jez_face_api/integrations/laravel.py`
- Modify: `laravel_sync.py`

- [ ] **Step 1: Create Laravel integration package marker**

Create `src/jez_face_api/integrations/__init__.py`:

```python
from jez_face_api.integrations.laravel import LaravelSync

__all__ = ["LaravelSync"]
```

- [ ] **Step 2: Move Laravel client with typed methods**

Create `src/jez_face_api/integrations/laravel.py`:

```python
import json
import logging

import requests

from jez_face_api.config import settings

logger = logging.getLogger(__name__)


class LaravelSync:
    def __init__(self) -> None:
        self.api_url = settings.LARAVEL_API_URL.rstrip("/")
        self.headers = {"Content-Type": "application/json", "Accept": "application/json"}
        if settings.LARAVEL_API_TOKEN:
            self.headers["Authorization"] = f"Bearer {settings.LARAVEL_API_TOKEN}"

    def get_users_face_data(self) -> dict[int, dict]:
        try:
            response = requests.get(
                f"{self.api_url}/v1/admin/face-data/all",
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as exc:
            logger.error("Failed to fetch face data from Laravel: %s", exc)
            return {}

        if payload.get("status") != "success":
            logger.warning("Laravel returned error: %s", payload.get("message"))
            return {}

        users_face_data: dict[int, dict] = {}
        for user_data in payload.get("data", []):
            user_id = user_data.get("id")
            face_data_json = user_data.get("u_face")
            if not user_id or not face_data_json:
                continue

            try:
                face_data = json.loads(face_data_json)
            except json.JSONDecodeError:
                logger.warning("Failed to parse face data for user %s", user_id)
                continue

            samples = self._extract_samples(face_data)
            if samples:
                users_face_data[int(user_id)] = {
                    "samples": samples,
                    "samples_count": len(samples),
                    "model": face_data.get("model", "unknown") if isinstance(face_data, dict) else "unknown",
                    "registered_at": face_data.get("registered_at") if isinstance(face_data, dict) else None,
                }

        return users_face_data

    def get_user_details(self, user_id: int) -> dict:
        try:
            response = requests.get(
                f"{self.api_url}/v1/admin/users/{user_id}",
                headers=self.headers,
                timeout=10,
            )
            response.raise_for_status()
            payload = response.json()
        except requests.exceptions.RequestException as exc:
            logger.error("Failed to fetch user details for %s: %s", user_id, exc)
            return {"name": "Unknown", "email": "", "phone": ""}

        if payload.get("status") != "success":
            return {"name": "Unknown", "email": "", "phone": ""}

        user = payload.get("data", {})
        return {
            "name": user.get("u_name", "Unknown"),
            "email": user.get("u_email", ""),
            "phone": user.get("u_phone", ""),
        }

    @staticmethod
    def _extract_samples(face_data: object) -> list[list[float]]:
        if isinstance(face_data, dict):
            raw_samples = face_data.get("samples") or face_data.get("descriptors") or []
        elif isinstance(face_data, list):
            raw_samples = face_data
        else:
            raw_samples = []

        valid_samples: list[list[float]] = []
        for sample in raw_samples:
            if isinstance(sample, list) and sample:
                valid_samples.append(sample)
            elif isinstance(sample, dict) and isinstance(sample.get("descriptor"), list):
                valid_samples.append(sample["descriptor"])
        return valid_samples


laravel_sync = LaravelSync()
```

- [ ] **Step 3: Replace root compatibility shim**

Replace `laravel_sync.py`:

```python
from jez_face_api.integrations.laravel import LaravelSync, laravel_sync

__all__ = ["LaravelSync", "laravel_sync"]
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest -q
```

Expected: existing tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/jez_face_api/integrations laravel_sync.py
git commit -m "refactor: move Laravel integration into package"
```

---

### Task 8: Add Backend Interface And DeepFace Compatibility Backend

**Files:**
- Create: `src/jez_face_api/recognition/base.py`
- Create: `src/jez_face_api/recognition/deepface_backend.py`
- Modify: `face_recognition_service.py`

- [ ] **Step 1: Create backend protocol**

Create `src/jez_face_api/recognition/base.py`:

```python
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class FaceEmbedding:
    embedding: list[float]
    confidence: float
    model: str


class FaceBackend(Protocol):
    def extract_embedding(self, image_base64: str) -> FaceEmbedding | None:
        ...

    def extract_embeddings(self, images_base64: list[str]) -> list[FaceEmbedding]:
        ...

    def model_info(self) -> dict:
        ...
```

- [ ] **Step 2: Create DeepFace backend using unique temp files**

Create `src/jez_face_api/recognition/deepface_backend.py`:

```python
import base64
import logging
import tempfile

import cv2
import numpy as np
from deepface import DeepFace

from jez_face_api.config import settings
from jez_face_api.recognition.base import FaceEmbedding

logger = logging.getLogger(__name__)


class DeepFaceBackend:
    def __init__(self) -> None:
        self.model_name = settings.DEEPFACE_MODEL
        self.detector_backend = settings.DEEPFACE_DETECTOR
        self._model_loaded = False
        self._preload_model()

    def _preload_model(self) -> None:
        try:
            DeepFace.build_model(self.model_name)
            self._model_loaded = True
        except Exception as exc:
            logger.error("Error loading DeepFace model %s: %s", self.model_name, exc)
            self._model_loaded = False

    def extract_embedding(self, image_base64: str) -> FaceEmbedding | None:
        image = self._decode_base64_image(image_base64)
        if image is None:
            return None

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=True) as temp_file:
            cv2.imwrite(temp_file.name, image)
            try:
                embeddings = DeepFace.represent(
                    img_path=temp_file.name,
                    model_name=self.model_name,
                    detector_backend=self.detector_backend,
                    enforce_detection=True,
                    align=True,
                )
            except Exception as exc:
                logger.error("DeepFace extraction failed: %s", exc)
                return None

        if not embeddings:
            return None

        best_face = max(
            embeddings,
            key=lambda item: item.get("facial_area", {}).get("w", 0)
            * item.get("facial_area", {}).get("h", 0),
        )
        return FaceEmbedding(
            embedding=best_face["embedding"],
            confidence=float(best_face.get("confidence", 0.99)),
            model=self.model_name,
        )

    def extract_embeddings(self, images_base64: list[str]) -> list[FaceEmbedding]:
        results: list[FaceEmbedding] = []
        for image in images_base64:
            embedding = self.extract_embedding(image)
            if embedding is not None:
                results.append(embedding)
        return results

    def model_info(self) -> dict:
        return {
            "backend": "deepface",
            "model_name": self.model_name,
            "detector_backend": self.detector_backend,
            "loaded": self._model_loaded,
        }

    @staticmethod
    def _decode_base64_image(base64_data: str) -> np.ndarray | None:
        if "," in base64_data:
            base64_data = base64_data.split(",", 1)[1]
        image_bytes = base64.b64decode(base64_data)
        image_array = np.frombuffer(image_bytes, np.uint8)
        return cv2.imdecode(image_array, cv2.IMREAD_COLOR)
```

- [ ] **Step 3: Keep root `face_recognition_service.py` compatibility until routes move**

Do not delete `face_recognition_service.py` in this task. Leave it untouched until Task 10 has route parity.

- [ ] **Step 4: Run tests**

Run:

```bash
pytest -q
```

Expected: existing tests pass without importing DeepFace during matching tests.

- [ ] **Step 5: Commit**

```bash
git add src/jez_face_api/recognition/base.py src/jez_face_api/recognition/deepface_backend.py
git commit -m "refactor: add recognition backend interface"
```

---

### Task 9: Add In-Memory Template Cache

**Files:**
- Create: `src/jez_face_api/cache.py`
- Test: `tests/test_matching.py`

- [ ] **Step 1: Add cache test**

Append to `tests/test_matching.py`:

```python
from jez_face_api.cache import FaceTemplateCache


def test_template_cache_builds_matrix_from_laravel_samples():
    cache = FaceTemplateCache()
    cache.reload_from_users_face_data(
        {
            101: {"samples": [[1.0, 0.0, 0.0], [0.9, 0.1, 0.0]]},
            202: {"samples": [[0.0, 1.0, 0.0]]},
        }
    )

    snapshot = cache.snapshot()

    assert snapshot.matrix.shape == (3, 3)
    assert snapshot.user_ids == [101, 101, 202]
```

- [ ] **Step 2: Implement cache**

Create `src/jez_face_api/cache.py`:

```python
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

        matrix = np.array(embeddings, dtype=np.float32) if embeddings else np.empty((0, 0), dtype=np.float32)
        with self._lock:
            self._matrix = matrix
            self._user_ids = user_ids

    def snapshot(self) -> FaceTemplateSnapshot:
        with self._lock:
            return FaceTemplateSnapshot(matrix=self._matrix.copy(), user_ids=list(self._user_ids))


face_template_cache = FaceTemplateCache()
```

- [ ] **Step 3: Run cache and matching tests**

Run:

```bash
pytest tests/test_matching.py -q
```

Expected: all tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/jez_face_api/cache.py tests/test_matching.py
git commit -m "feat: add in-memory face template cache"
```

---

### Task 10: Move Face Routes Into Package

**Files:**
- Create: `src/jez_face_api/routes/faces.py`
- Modify: `src/jez_face_api/app.py`
- Test: `tests/test_api_contract.py`

- [ ] **Step 1: Implement face routes with current DeepFace compatibility**

Create `src/jez_face_api/routes/faces.py`:

```python
import time

from fastapi import APIRouter, Depends, HTTPException

from jez_face_api.config import settings
from jez_face_api.integrations.laravel import laravel_sync
from jez_face_api.recognition.deepface_backend import DeepFaceBackend
from jez_face_api.schemas import IdentifyRequest, QualityRequest, RegisterRequest, VerifyRequest
from jez_face_api.security import require_internal_token

router = APIRouter(prefix="/api/v1/faces", dependencies=[Depends(require_internal_token)])
backend = DeepFaceBackend()


@router.get("/model-info")
def model_info() -> dict:
    return backend.model_info()


@router.get("/status")
def status() -> dict:
    users_data = laravel_sync.get_users_face_data()
    return {
        "status": "operational",
        "service": "JEZ Face Recognition API",
        "version": "0.1.0",
        "model": backend.model_info().get("model_name", "unknown"),
        "total_users": len(users_data),
        "face_threshold": settings.FACE_MATCH_THRESHOLD,
    }


@router.post("/register")
def register_faces(request: RegisterRequest) -> dict:
    start_time = time.time()
    if len(request.images) < 3 or len(request.images) > 20:
        raise HTTPException(status_code=422, detail="Minimal 3 foto dan maksimal 20 foto diperlukan")

    embeddings = backend.extract_embeddings(request.images)
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
            "user_id": request.user_id,
        },
    }


@router.post("/identify")
def identify_face(request: IdentifyRequest) -> dict:
    from face_recognition_service import face_service

    start_time = time.time()
    descriptor = face_service.extract_descriptor(request.image)
    if not descriptor:
        return {"status": "error", "message": "Wajah tidak terdeteksi dalam gambar.", "data": None}

    users_face_data = laravel_sync.get_users_face_data()
    if not users_face_data:
        return {"status": "not_found", "message": "Tidak ada data wajah terdaftar.", "data": None}

    match_result = face_service.find_matching_user(descriptor, users_face_data)
    processing_time = time.time() - start_time
    if not match_result["matched"]:
        return {
            "status": "not_found",
            "message": f"Wajah tidak dikenali. Confidence: {match_result['confidence']:.2f}",
            "data": {"confidence": match_result["confidence"], "processing_time": processing_time},
        }

    user_details = laravel_sync.get_user_details(match_result["user_id"])
    return {
        "status": "success",
        "message": "Wajah berhasil dikenali.",
        "data": {
            "user": {"id": match_result["user_id"], "name": user_details.get("name", "Unknown")},
            "match": {
                "distance": match_result["distance"],
                "confidence": match_result["confidence"],
                "threshold": settings.FACE_MATCH_THRESHOLD,
            },
            "processing_time": processing_time,
        },
    }


@router.post("/quality")
def assess_quality(request: QualityRequest) -> dict:
    from face_recognition_service import face_service

    return face_service.assess_quality(request.image)


@router.post("/verify")
def verify_faces(request: VerifyRequest) -> dict:
    from face_recognition_service import face_service

    result = face_service.verify_faces(request.image1, request.image2)
    return {
        "status": "success" if result["verified"] else "failed",
        "verified": result["verified"],
        "confidence": result["confidence"],
        "distance": result["distance"],
        "threshold": result.get("threshold", settings.FACE_MATCH_THRESHOLD),
        "model": result.get("model", backend.model_info().get("model_name", "unknown")),
    }
```

- [ ] **Step 2: Register face router in app factory**

Modify `src/jez_face_api/app.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from jez_face_api.config import settings
from jez_face_api.routes.faces import router as faces_router
from jez_face_api.routes.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="JEZ Face Recognition API",
        description="Private face identity service for JEZ attendance",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(health_router)
    app.include_router(faces_router)
    return app


app = create_app()
```

- [ ] **Step 3: Run API contract tests**

Run:

```bash
pytest tests/test_api_contract.py -q
```

Expected: tests pass.

- [ ] **Step 4: Commit**

```bash
git add src/jez_face_api/routes/faces.py src/jez_face_api/app.py
git commit -m "refactor: move face routes into package"
```

---

### Task 11: Add InsightFace Backend Behind A Feature Flag

**Files:**
- Modify: `requirements.txt`
- Create: `src/jez_face_api/recognition/insightface_backend.py`
- Modify: `src/jez_face_api/routes/faces.py`

- [ ] **Step 1: Add InsightFace dependencies**

Modify `requirements.txt` by adding:

```text

# InsightFace target backend
insightface>=0.7.3
onnxruntime>=1.17.0
```

- [ ] **Step 2: Implement InsightFace backend**

Create `src/jez_face_api/recognition/insightface_backend.py`:

```python
import base64
import logging

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from jez_face_api.config import settings
from jez_face_api.recognition.base import FaceEmbedding

logger = logging.getLogger(__name__)


class InsightFaceBackend:
    def __init__(self) -> None:
        self.model_pack = settings.INSIGHTFACE_MODEL_PACK
        self.det_size = settings.INSIGHTFACE_DET_SIZE
        self.provider = settings.INSIGHTFACE_PROVIDER
        self.app = FaceAnalysis(name=self.model_pack, providers=[self.provider])
        self.app.prepare(ctx_id=-1, det_size=(self.det_size, self.det_size))

    def extract_embedding(self, image_base64: str) -> FaceEmbedding | None:
        image = self._decode_base64_image(image_base64)
        if image is None:
            return None

        faces = self.app.get(image)
        if not faces:
            return None

        best_face = max(faces, key=lambda face: (face.bbox[2] - face.bbox[0]) * (face.bbox[3] - face.bbox[1]))
        embedding = best_face.normed_embedding.astype(np.float32).tolist()
        return FaceEmbedding(
            embedding=embedding,
            confidence=float(best_face.det_score),
            model=self.model_pack,
        )

    def extract_embeddings(self, images_base64: list[str]) -> list[FaceEmbedding]:
        results: list[FaceEmbedding] = []
        for image in images_base64:
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

    @staticmethod
    def _decode_base64_image(base64_data: str) -> np.ndarray | None:
        if "," in base64_data:
            base64_data = base64_data.split(",", 1)[1]
        image_bytes = base64.b64decode(base64_data)
        image_array = np.frombuffer(image_bytes, np.uint8)
        return cv2.imdecode(image_array, cv2.IMREAD_COLOR)
```

- [ ] **Step 3: Add backend factory in face routes**

Modify top of `src/jez_face_api/routes/faces.py` to select backend:

```python
from jez_face_api.recognition.deepface_backend import DeepFaceBackend
from jez_face_api.recognition.insightface_backend import InsightFaceBackend


def create_backend():
    if settings.FACE_BACKEND == "insightface":
        return InsightFaceBackend()
    return DeepFaceBackend()


backend = create_backend()
```

- [ ] **Step 4: Install dependencies and run tests**

Run:

```bash
python -m pip install -r requirements.txt
pytest -q
```

Expected: tests pass.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt src/jez_face_api/recognition/insightface_backend.py src/jez_face_api/routes/faces.py
git commit -m "feat: add InsightFace backend option"
```

---

### Task 12: Add Cache Reload Endpoint And Cached Identify Path

**Files:**
- Modify: `src/jez_face_api/routes/faces.py`
- Modify: `tests/test_api_contract.py`

- [ ] **Step 1: Add reload-cache contract test**

Append to `tests/test_api_contract.py`:

```python
from jez_face_api.config import settings


def test_reload_cache_requires_valid_internal_token():
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/faces/reload-cache",
        headers={"X-Internal-Token": settings.INTERNAL_API_TOKEN},
    )

    assert response.status_code == 200
    assert response.json()["status"] in {"success", "error"}
```

- [ ] **Step 2: Add reload-cache endpoint**

Add to `src/jez_face_api/routes/faces.py`:

```python
from jez_face_api.cache import face_template_cache


@router.post("/reload-cache")
def reload_cache() -> dict:
    users_face_data = laravel_sync.get_users_face_data()
    face_template_cache.reload_from_users_face_data(users_face_data)
    return {
        "status": "success",
        "templates": len(face_template_cache.snapshot().user_ids),
        "users": len(users_face_data),
    }
```

- [ ] **Step 3: Update identify route to use cache when available**

In `identify_face`, replace the Laravel fetch and old matcher block with:

```python
    snapshot = face_template_cache.snapshot()
    if snapshot.matrix.size == 0:
        users_face_data = laravel_sync.get_users_face_data()
        face_template_cache.reload_from_users_face_data(users_face_data)
        snapshot = face_template_cache.snapshot()

    if snapshot.matrix.size == 0:
        return {"status": "not_found", "message": "Tidak ada data wajah terdaftar.", "data": None}

    from jez_face_api.recognition.matching import MatchConfig, match_embedding

    match_result = match_embedding(
        np.array(descriptor, dtype=np.float32),
        snapshot.matrix,
        snapshot.user_ids,
        MatchConfig(
            auto_match_threshold=settings.FACE_AUTO_MATCH_THRESHOLD,
            ambiguous_threshold=settings.FACE_AMBIGUOUS_THRESHOLD,
            min_margin=settings.FACE_MIN_MARGIN,
        ),
    )
```

Also add this import at the top:

```python
import numpy as np
```

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/test_api_contract.py tests/test_matching.py -q
```

Expected: tests pass.

- [ ] **Step 5: Commit**

```bash
git add src/jez_face_api/routes/faces.py tests/test_api_contract.py
git commit -m "feat: add face template cache reload endpoint"
```

---

### Task 13: Final Cleanup Of Root Files And Docker

**Files:**
- Modify: `Dockerfile`
- Delete after parity confirmed: `main_alternative.py`
- Delete after parity confirmed: `face_recognition_service.py`
- Delete after parity confirmed: `download_models.py`
- Delete after parity confirmed: `test_deepface.py`
- Review: `server.log`
- Review: `royyan.txt`
- Review: `DATABASE_INFO.txt`

- [ ] **Step 1: Update Dockerfile to use package app**

Replace `Dockerfile`:

```dockerfile
FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY main.py ./

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "jez_face_api.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: Confirm legacy root files are unused**

Run:

```bash
rg "main_alternative|face_recognition_service|download_models|test_deepface" .
```

Expected: only planned archive references or no references after routes fully use packaged backends.

- [ ] **Step 3: Remove obsolete root files after no references remain**

Run:

```bash
rm main_alternative.py face_recognition_service.py download_models.py test_deepface.py
```

Expected: files are removed.

- [ ] **Step 4: Decide non-code artifact handling**

Run:

```bash
mkdir -p docs/archive/runtime-artifacts
mv DATABASE_INFO.txt docs/archive/runtime-artifacts/DATABASE_INFO.txt
mv royyan.txt docs/archive/runtime-artifacts/royyan.txt
rm -f server.log
```

Expected: root has no logs or personal notes.

- [ ] **Step 5: Run final verification**

Run:

```bash
pytest -q
python -m ruff check .
```

Expected: tests pass and Ruff reports no blocking issues.

- [ ] **Step 6: Commit**

```bash
git add Dockerfile docs src tests main.py requirements.txt pyproject.toml README.md scripts
git add -u
git commit -m "chore: finalize clean project structure"
```

---

## Verification Checklist

- [ ] `rg --files -g '*.sh'` returns only files under `scripts/`.
- [ ] `rg --files -g '*.md'` returns root `README.md`, active docs under `docs/`, and archived historical docs under `docs/archive/`.
- [ ] `scripts/setup.sh` works from any checkout location.
- [ ] `scripts/start.sh` starts the FastAPI app from `src/jez_face_api/app.py`.
- [ ] `scripts/smoke_test.sh http://127.0.0.1:8000` hits real endpoints.
- [ ] `pytest -q` passes.
- [ ] `python -m ruff check .` passes or reports only issues fixed before merge.
- [ ] `FACE_BACKEND=deepface` keeps the existing integration working.
- [ ] `FACE_BACKEND=insightface` loads `buffalo_m` after dependencies and models are installed.
- [ ] `/api/v1/faces/reload-cache` refreshes the in-memory matrix.
- [ ] `/api/v1/faces/identify` uses cached templates instead of fetching all Laravel face data every request once cache is warm.
- [ ] Non-health face endpoints require `X-Internal-Token`.

## Self-Review

- Spec coverage: The plan cleans all root `.sh` files, consolidates all root `.md` files, creates a clearer package structure, keeps current DeepFace compatibility, and adds the planned InsightFace/cached matching path.
- Placeholder scan: No task uses `TBD`, `TODO`, or unnamed future work as an implementation step.
- Type consistency: `MatchConfig`, `MatchResult`, `FaceTemplateCache`, `Settings`, and route names are consistent across tasks.
