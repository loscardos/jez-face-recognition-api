# Production Runbook

Operational guide for running the JEZ Face Recognition API in production with Docker.

## Service Role

This service is private. Laravel owns public attendance routes, user authorization, attendance writes, and face template storage. The Face API only handles image quality checks, embedding extraction, in-memory template matching, and cache reloads from Laravel.

Never expose this API directly to the public internet. Put it on a private Docker network, localhost binding, VPN-only subnet, or behind an internal reverse proxy.

## Production Requirements

- Docker host with enough CPU for ONNXRuntime inference.
- Network access from Face API to Laravel internal API.
- Matching `INTERNAL_API_TOKEN` in Laravel and this service.
- Matching `LARAVEL_API_TOKEN` in Laravel and this service.
- Laravel scheduler running, so `face:sync-cache-if-stale` can keep the Face API cache fresh.
- Persistent model volume for InsightFace models.

## Required Environment

```env
HOST=0.0.0.0
PORT=8000
DEBUG=false

LARAVEL_API_URL=https://your-laravel-internal-host/api
LARAVEL_API_TOKEN=replace-with-strong-shared-token
INTERNAL_API_TOKEN=replace-with-strong-shared-token

FACE_BACKEND=insightface
MIN_DETECTION_CONFIDENCE=0.8

INSIGHTFACE_MODEL_PACK=buffalo_m
INSIGHTFACE_DET_SIZE=640
INSIGHTFACE_PROVIDER=CPUExecutionProvider

FACE_AUTO_MATCH_THRESHOLD=0.45
FACE_AMBIGUOUS_THRESHOLD=0.38
FACE_MIN_MARGIN=0.05
```

Notes:

- `INTERNAL_API_TOKEN` protects non-health Face API endpoints.
- `LARAVEL_API_TOKEN` is used by Face API when pulling templates/user details from Laravel.
- Rotate both tokens when moving from local/staging to production.
- Keep `DEBUG=false` in production.

## Build Image

From the repository root:

```bash
docker build -t jez-face-recognition-api:$(git rev-parse --short HEAD) .
```

Optional stable tag:

```bash
docker tag jez-face-recognition-api:$(git rev-parse --short HEAD) jez-face-recognition-api:latest
```

## Run Container

Recommended single-host example:

```bash
docker volume create jez-face-models

docker run -d \
  --name jez-face-api \
  --restart unless-stopped \
  -p 127.0.0.1:8000:8000 \
  --env-file /opt/jez-face-api/.env \
  -v jez-face-models:/root/.insightface/models \
  jez-face-recognition-api:latest
```

If Laravel is another Docker service, place both containers on the same private Docker network and set `LARAVEL_API_URL` to the Laravel service name, for example:

```env
LARAVEL_API_URL=http://jez-laravel:8000/api
```

If Laravel is on the host from a Linux container, either use a private host IP or run with host networking. Avoid relying on public URLs when an internal route is available.

## First Boot

The first quality/recognition call may download the `buffalo_m` model into `/root/.insightface/models`. With the model volume mounted, this cost happens once per host/volume.

Warm the model after deploy:

```bash
python - <<'PY'
from PIL import Image
Image.new('RGB', (320, 320), 'black').save('/tmp/blank-face-quality.jpg', 'JPEG')
PY

curl -sS -X POST "$FACE_API_URL/api/v1/faces/quality" \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" \
  -F image=@/tmp/blank-face-quality.jpg
```

Expected response for a blank image is HTTP 200 with `score: 0.0` and feedback that no face was detected. That confirms the model loads and inference runs.

## Smoke Test

Set variables:

```bash
export FACE_API_URL=http://127.0.0.1:8000
export INTERNAL_API_TOKEN=replace-with-strong-shared-token
```

Run health check:

```bash
curl -fsS "$FACE_API_URL/health"
```

Check protected status:

```bash
curl -fsS \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" \
  "$FACE_API_URL/api/v1/faces/status"
```

Reload templates from Laravel:

```bash
curl -fsS -X POST \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" \
  "$FACE_API_URL/api/v1/faces/reload-cache"
```

Check cache after reload:

```bash
curl -fsS \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" \
  "$FACE_API_URL/api/v1/faces/status"
```

Expected:

- `/health` returns HTTP 200.
- `/status` returns HTTP 200.
- `/reload-cache` returns HTTP 200 with non-zero `templates` when production has enrolled templates.
- `/status` shows `cached_templates` equal to the latest template count and has a non-empty `cache_fingerprint`.

## Cache Operations

The template cache is in process memory. It is rebuilt from Laravel `user_face_templates` through `/api/v1/faces/reload-cache`.

Reload manually after template changes:

```bash
curl -fsS -X POST \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" \
  "$FACE_API_URL/api/v1/faces/reload-cache"
```

The reload endpoint refuses to replace an existing cache when Laravel returns zero templates. In that case it returns HTTP 503 and preserves the old cache.

For multi-replica deployments, every replica has its own memory cache. Reload each replica or restart replicas after template changes. A single load-balanced reload request only refreshes the replica that receives it.

## Laravel Integration Checklist

- `FACE_API_URL` in Laravel points to this service's internal URL.
- Laravel `FACE_API_TOKEN` matches Face API `INTERNAL_API_TOKEN`.
- Face API `LARAVEL_API_TOKEN` matches Laravel internal API token.
- Laravel scheduler is active:

```bash
php artisan schedule:run
```

Production usually runs that every minute via cron or a scheduler worker/container.

## Monitoring

Minimum probes:

```bash
curl -fsS "$FACE_API_URL/health"

curl -fsS \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" \
  "$FACE_API_URL/api/v1/faces/status"
```

Watch these fields from `/status`:

- `cached_templates`
- `cache_fingerprint`
- `model`
- `backend`
- `face_threshold`

Useful logs:

```bash
docker logs --tail=200 jez-face-api
```

## Troubleshooting

### `/reload-cache` returns HTTP 503

Meaning: Laravel returned zero templates or Face API could not fetch Laravel data.

Check:

```bash
curl -fsS \
  -H "X-Internal-Token: $LARAVEL_API_TOKEN" \
  "$LARAVEL_API_URL/v1/admin/face-data/all"
```

Then verify token, Laravel URL, network route, and whether `user_face_templates` has rows.

### `/quality` returns `insightface backend unavailable`

Check logs:

```bash
docker logs --tail=200 jez-face-api
```

Common causes:

- Model download failed.
- Model volume is not writable.
- Container has no network access during first model download.
- ONNXRuntime cannot load on the host architecture.

Fix the underlying issue and restart the container:

```bash
docker restart jez-face-api
```

### First request is slow

The first request may download and initialize `buffalo_m`. Use a persistent model volume and warm the model immediately after deployment.

### `cached_templates` is stale

Run manual reload, then check status:

```bash
curl -fsS -X POST \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" \
  "$FACE_API_URL/api/v1/faces/reload-cache"

curl -fsS \
  -H "X-Internal-Token: $INTERNAL_API_TOKEN" \
  "$FACE_API_URL/api/v1/faces/status"
```

If stale again later, check Laravel scheduler and `face:sync-cache-if-stale` logs.

## Rollback

Keep the previous image tag before deploying a new one.

```bash
docker rm -f jez-face-api

docker run -d \
  --name jez-face-api \
  --restart unless-stopped \
  -p 127.0.0.1:8000:8000 \
  --env-file /opt/jez-face-api/.env \
  -v jez-face-models:/root/.insightface/models \
  jez-face-recognition-api:<previous-tag>
```

After rollback, run the smoke test and reload cache.

## Production Deploy Checklist

- Image builds successfully.
- `.env` contains production tokens, not local defaults.
- Service is private/internal only.
- Model volume is mounted.
- `/health` passes.
- `/quality` returns HTTP 200 for a blank-image model warmup.
- `/reload-cache` returns non-zero templates.
- `/status` shows expected cache count and fingerprint.
- Laravel scheduler is running.
- Attendance enroll and identify flows are tested from Laravel UI/API.
