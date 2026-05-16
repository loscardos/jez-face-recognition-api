# InsightFace Migration

## Target

Use InsightFace `buffalo_m` with ONNXRuntime CPU provider, cached template matrix, top-2 margin checks, and Laravel-owned business decisions.

## Required Migration Rules

- Re-enroll all active users after switching to InsightFace.
- Do not compare old DeepFace embeddings with InsightFace embeddings.
- Calibrate `FACE_AUTO_MATCH_THRESHOLD`, `FACE_AMBIGUOUS_THRESHOLD`, and `FACE_MIN_MARGIN` against real JEZ employee data.
- DeepFace compatibility has been removed from this service.
- Existing DeepFace embeddings are invalid for InsightFace matching and must be replaced.

## Target Table

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
