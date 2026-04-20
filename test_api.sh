#!/bin/bash
# Quick test of Face Recognition API

API_URL="${1:-http://localhost:8000}"

echo "========================================"
echo "Face Recognition API - Quick Test"
echo "========================================"
echo ""
echo "Testing API: $API_URL"
echo ""

# Test 1: Health check
echo "1. Health Check..."
curl -s "$API_URL/health" | python3 -m json.tool || echo "Failed"
echo ""

# Test 2: API Status
echo "2. API Status..."
curl -s "$API_URL/api/status" | python3 -m json.tool || echo "Failed"
echo ""

# Test 3: Sync Face Data (if Laravel is configured)
echo "3. Sync Face Data from Laravel..."
curl -s "$API_URL/api/faces/sync" | python3 -m json.tool || echo "Failed"
echo ""

# To test image processing, you need to provide a base64-encoded image
echo "4. To test face encoding/identification, provide a face image"
echo "   Example:"
echo "   curl -X POST $API_URL/api/faces/quality \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"image_data\": \"data:image/png;base64,iVBORw0KGgoAAAA...\"}'"
echo ""
echo "========================================"
