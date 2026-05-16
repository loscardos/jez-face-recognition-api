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

