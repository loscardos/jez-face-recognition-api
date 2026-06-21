# Face Recognition API AI Guide

`sz-face-recognition-api` is a private FastAPI service for JEZ attendance face
identity checks. It is frozen by default under the current workspace policy
unless an explicit biometric/support-app task opens the scope.

## Control Plane

Read these before changing code:

1. `../AGENTS.md`
2. `../sz-all-projects/AGENTS.md`
3. `../sz-all-projects/status.yml`
4. `../sz-all-projects/migration/freeze-lift-decision.yml`
5. `../sz-all-projects/migration/parallel-workstream-freeze-lift.yml`
6. `../sz-all-projects/projects/sz-face-recognition-api/ai-context.yml`
7. `../sz-all-projects/projects/sz-face-recognition-api/project.yml`
8. `../sz-all-projects/projects/sz-face-recognition-api/status.yml`
9. `../sz-all-projects/projects/sz-face-recognition-api/contracts.yml`
10. `../sz-all-projects/projects/sz-face-recognition-api/change-impact.yml`
11. `../sz-all-projects/projects/sz-face-recognition-api/plans/plan-registry.yml`
12. `../sz-all-projects/projects/sz-face-recognition-api/backlog.yml`
13. `../sz-all-projects/projects/sz-face-recognition-api/evidence.yml`

Do not use archived `sz-projects-managements` docs as active guidance.

## Scope

- Owns face registration, identification, verification, quality checks,
  embedding cache behavior, and private FastAPI endpoints.
- Uses InsightFace `buffalo_m`, ONNXRuntime, cached embeddings, and vectorized
  matching.
- DeepFace/TensorFlow support has been removed; old DeepFace embeddings require
  re-enrollment before production use.
- Does not own Laravel attendance business workflow or IAM. Integrate through
  explicit contracts only.

## Commands

```bash
scripts/setup.sh
scripts/start.sh
scripts/smoke_test.sh
python -m pytest
python -m ruff check .
curl http://127.0.0.1:8000/health
docker build -t jez-face-recognition-api:$(git rev-parse --short HEAD) .
```

`scripts/setup.sh` creates `.venv`, installs `requirements.txt`, copies
`.env.example` to `.env` when missing, and creates local `logs` and `face_data`
directories.

## Configuration And Secrets

- Protected face endpoints require `X-Internal-Token`.
- `.env` is local runtime state. Do not commit real tokens, biometric data,
  face images, embeddings, logs, or model-cache artifacts.
- Do not read or copy local `.env` during metadata-only work.
- `.env.example` values are placeholders only; replace
  `change-this-in-production` before any real deployment.

## Tests

Tests live under `tests/`:

- `tests/test_security.py`
- `tests/test_api_contract.py`
- `tests/test_matching.py`

Use focused pytest paths for narrow behavior changes.

## Docs Gate

Any approved change must update the relevant status, backlog, evidence, and
change-impact docs under `../sz-all-projects/projects/sz-face-recognition-api/`,
then run:

```bash
cd ../sz-all-projects
python3 scripts/validate_docs.py --mode archive_ready --root .
```
