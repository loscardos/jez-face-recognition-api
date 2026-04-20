#!/bin/bash
# Face Recognition System - Start Server

set -e

PROJECT_DIR="/home/royyan/projects/face-attendance-ai"
cd "$PROJECT_DIR"

echo "Starting Face Recognition Backend..."
echo "Project: $PROJECT_DIR"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Running setup..."
    bash setup.sh
    echo ""
fi

# Activate virtual environment
source venv/bin/activate

echo "Configuration:"
echo "  Face threshold: $(grep FACE_MATCH_THRESHOLD .env | cut -d= -f2)"
echo "  Laravel API: $(grep LARAVEL_API_URL .env | cut -d= -f2)"
echo ""

echo "Starting server..."
echo "API will be available at: http://localhost:8000"
echo "API Documentation at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "========================================"
echo ""

python main.py
