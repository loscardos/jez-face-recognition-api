#!/bin/bash
# Start DeepFace Server

cd /home/royyan/projects/face-attendance-ai
source venv/bin/activate

# Set environment
export TF_ENABLE_ONEDNN_OPTS=0
export DEEPFACE_HOME=/home/royyan/projects/face-attendance-ai/.deepface

echo "Starting DeepFace Server on port 8001..."
echo "Model: Facenet"
echo "Detector: opencv"
echo ""

python main.py
