#!/usr/bin/env python3
"""
Pre-download DeepFace models untuk menghindari download saat runtime pertama
Jalankan sekali sebelum deploy: python download_models.py
"""
import os
from deepface import DeepFace
from config import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

print("="*60)
print("DeepFace Model Downloader")
print("="*60)

# Set environment variable
os.environ['DEEPFACE_HOME'] = config.DEEPFACE_HOME

print(f"\nModel: {config.DEEPFACE_MODEL}")
print(f"Detector: {config.DEEPFACE_DETECTOR}")
print(f"Cache Directory: {config.DEEPFACE_HOME}\n")

# Create directory
os.makedirs(config.DEEPFACE_HOME, exist_ok=True)

try:
    print("Downloading face recognition model...")
    model = DeepFace.build_model(config.DEEPFACE_MODEL)
    print(f"✓ {config.DEEPFACE_MODEL} model downloaded successfully")
except Exception as e:
    print(f"✗ Error downloading model: {e}")

try:
    print(f"\nDownloading face detector ({config.DEEPFACE_DETECTOR})...")
    # Trigger detector download dengan dummy detection
    import cv2
    import numpy as np
    
    # Create dummy image
    dummy = np.zeros((100, 100, 3), dtype=np.uint8)
    temp_path = "/tmp/dummy.jpg"
    cv2.imwrite(temp_path, dummy)
    
    # This will download the detector
    DeepFace.detectFace(temp_path, detector_backend=config.DEEPFACE_DETECTOR)
    
    # Cleanup
    if os.path.exists(temp_path):
        os.remove(temp_path)
    
    print(f"✓ {config.DEEPFACE_DETECTOR} detector downloaded successfully")
except Exception as e:
    print(f"⚠ Detector might be already cached or error: {e}")

print("\n" + "="*60)
print("Model download complete!")
print("="*60)
print(f"\nModels are cached at: {config.DEEPFACE_HOME}")
print("You can now start the server with: python main.py")
