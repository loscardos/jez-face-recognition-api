#!/usr/bin/env bash
set -euo pipefail

API_URL="${1:-http://127.0.0.1:8000}"
TOKEN="${INTERNAL_API_TOKEN:-change-this-in-production}"

echo "Health:"
curl -fsS "$API_URL/health" | python -m json.tool

echo "Model info:"
curl -fsS -H "X-Internal-Token: $TOKEN" "$API_URL/api/v1/faces/model-info" | python -m json.tool

