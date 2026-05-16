# API

Non-health endpoints require the `X-Internal-Token` header.

## `GET /health`

Returns service health.

## `POST /api/v1/faces/register`

Registers 3 to 20 face samples. Send as `multipart/form-data`.

```bash
curl -X POST "$API_URL/api/v1/faces/register" \
  -H "X-Internal-Token: $TOKEN" \
  -F "user_id=123" \
  -F "images=@face-1.jpg" \
  -F "images=@face-2.jpg" \
  -F "images=@face-3.jpg"
```

## `POST /api/v1/faces/identify`

Identifies one face image against the in-memory template cache. Send as `multipart/form-data`.

```bash
curl -X POST "$API_URL/api/v1/faces/identify" \
  -H "X-Internal-Token: $TOKEN" \
  -F "image=@face.jpg" \
  -F 'location={"lat":-6.2,"lng":106.8}' \
  -F 'metadata={"device":"mobile"}'
```

## `POST /api/v1/faces/reload-cache`

Reloads face templates from Laravel into memory.

## `POST /api/v1/faces/quality`

Checks whether an image is usable for enrollment. Send `image` as a multipart file.

## `POST /api/v1/faces/verify`

Compares two face images. Send `image1` and `image2` as multipart files.

## `GET /api/v1/faces/status`

Returns service status, model, threshold, and cache size.

## `GET /api/v1/faces/model-info`

Returns backend model loading information.
