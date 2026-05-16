# JEZ Face Recognition API

Private FastAPI service for JEZ attendance face identity checks.

## Current Status

The runtime uses InsightFace `buffalo_m`, ONNXRuntime, cached embeddings, and vectorized matching. DeepFace/TensorFlow support has been removed, so old DeepFace embeddings must be re-enrolled before production use.

## Quick Start

```bash
scripts/setup.sh
scripts/start.sh
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Protected face endpoints require:

```http
X-Internal-Token: change-this-in-production
```

## Main Endpoints

- `GET /health`
- `POST /api/v1/faces/register`
- `POST /api/v1/faces/identify`
- `POST /api/v1/faces/quality`
- `POST /api/v1/faces/verify`
- `POST /api/v1/faces/reload-cache`
- `GET /api/v1/faces/status`
- `GET /api/v1/faces/model-info`

## Documentation

- `docs/architecture.md`
- `docs/api.md`
- `docs/operations.md`
- `docs/improvements.md`
- `docs/migration-insightface.md`
- `docs/archive/`
