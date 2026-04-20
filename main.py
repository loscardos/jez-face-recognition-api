"""
Face Recognition API Backend - DeepFace Implementation
FastAPI application for face recognition and attendance using DeepFace library
"""
import logging
import json
import time
from typing import List, Optional, Dict
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import base64
import numpy as np
from face_recognition_service import face_service
from laravel_sync import laravel_sync
from config import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Face Recognition API (DeepFace)",
    description="Face recognition and attendance API using DeepFace library - Optimized for 200+ users",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request/Response Models
class RegisterRequest(BaseModel):
    images: List[str]  # Base64 encoded images
    user_id: Optional[int] = None  # Optional user ID untuk tracking

class IdentifyRequest(BaseModel):
    image: str  # Base64 encoded image
    location: Optional[Dict] = None  # Optional location data
    metadata: Optional[Dict] = None  # Optional metadata (device, timestamp, etc)

class QualityRequest(BaseModel):
    image: str  # Base64 encoded image

class VerifyRequest(BaseModel):
    image1: str  # Base64 encoded image 1
    image2: str  # Base64 encoded image 2

class RegisterResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict] = None

class IdentifyResponse(BaseModel):
    status: str
    message: str
    data: Optional[Dict] = None

class QualityResponse(BaseModel):
    status: str
    score: float
    is_acceptable: bool
    feedback: str

class StatusResponse(BaseModel):
    status: str
    service: str
    version: str
    model: str
    total_users: int
    face_threshold: float

# Health Check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    model_info = face_service.get_model_info()
    return {
        "status": "healthy",
        "service": "face_recognition",
        "version": "2.0.0",
        "library": "deepface",
        "model": model_info['model_name'],
        "detector": model_info['detector_backend'],
        "model_loaded": model_info['loaded']
    }

# Laravel-compatible endpoints

@app.post("/api/v1/faces/register", response_model=RegisterResponse)
async def register_faces(request: RegisterRequest):
    """
    Register multiple face samples for a user menggunakan DeepFace
    Laravel calls this endpoint for face registration from /data_user
    """
    start_time = time.time()
    try:
        logger.info(f"Registration request for user {request.user_id}: {len(request.images)} images")
        
        if len(request.images) < 3 or len(request.images) > 20:
            raise HTTPException(
                status_code=422,
                detail="Minimal 3 foto dan maksimal 20 foto diperlukan untuk registrasi"
            )

        # Extract descriptors dari semua images
        descriptors = face_service.extract_multiple_descriptors(request.images)
        processing_time = time.time() - start_time
        
        logger.info(f"Extracted {len(descriptors)} descriptors in {processing_time:.2f}s")

        if len(descriptors) < 3:
            return {
                "status": "error",
                "message": f"Tidak cukup wajah terdeteksi. Hanya {len(descriptors)} dari {len(request.images)} foto yang berhasil diproses. Minimal 3 foto diperlukan.",
                "data": {
                    "registered": False,
                    "registered_count": len(descriptors),
                    "required_count": 3,
                    "processing_time": processing_time
                }
            }

        return {
            "status": "success",
            "message": f"Wajah berhasil didaftar dengan {len(descriptors)} template menggunakan {config.DEEPFACE_MODEL}.",
            "data": {
                "registered": True,
                "descriptor_count": len(descriptors),
                "descriptors": descriptors,
                "model": config.DEEPFACE_MODEL,
                "registered_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "processing_time": processing_time,
                "user_id": request.user_id
            }
        }

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/faces/identify", response_model=IdentifyResponse)
async def identify_face(request: IdentifyRequest):
    """
    Identify user from face image untuk absensi di /manual-attendance
    Laravel calls this endpoint for face identification
    """
    start_time = time.time()
    try:
        logger.info("Identification request received")
        
        # Extract descriptor dari image
        descriptor = face_service.extract_descriptor(request.image)

        if not descriptor:
            return {
                "status": "error",
                "message": "Wajah tidak terdeteksi dalam gambar. Silakan coba lagi dengan pencahayaan lebih baik.",
                "data": None
            }

        # Get all users' face data dari Laravel
        users_face_data = laravel_sync.get_users_face_data()

        if not users_face_data:
            return {
                "status": "not_found",
                "message": "Tidak ada data wajah terdaftar dalam sistem.",
                "data": None
            }

        # Find matching user
        match_result = face_service.find_matching_user(descriptor, users_face_data)
        processing_time = time.time() - start_time
        
        logger.info(f"Match result: {match_result}")

        if not match_result['matched']:
            return {
                "status": "not_found",
                "message": f"Wajah tidak dikenali. Confidence: {match_result['confidence']:.2f}",
                "data": {
                    "confidence": match_result['confidence'],
                    "threshold": config.FACE_MATCH_THRESHOLD,
                    "processing_time": processing_time
                }
            }

        # Get user details
        user_details = laravel_sync.get_user_details(match_result['user_id'])

        return {
            "status": "success",
            "message": "Wajah berhasil dikenali.",
            "data": {
                "user": {
                    "id": match_result['user_id'],
                    "name": user_details.get('name', 'Unknown'),
                    "email": user_details.get('email', ''),
                    "phone": user_details.get('phone', ''),
                },
                "match": {
                    "distance": match_result['distance'],
                    "confidence": match_result['confidence'],
                    "threshold": config.FACE_MATCH_THRESHOLD,
                },
                "processing_time": processing_time,
                "model": config.DEEPFACE_MODEL
            }
        }

    except Exception as e:
        logger.error(f"Identification error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/faces/quality")
async def assess_quality(request: QualityRequest):
    """
    Assess image quality before registration
    Laravel calls this endpoint for quality assessment
    """
    try:
        quality_result = face_service.assess_quality(request.image)

        return {
            "status": quality_result['status'],
            "score": quality_result['score'],
            "is_acceptable": quality_result['is_acceptable'],
            "feedback": quality_result['feedback'],
            "details": quality_result.get('details', {})
        }

    except Exception as e:
        logger.error(f"Quality assessment error: {str(e)}")
        return {
            "status": "error",
            "score": 0.0,
            "is_acceptable": False,
            "feedback": f"Error: {str(e)}"
        }

@app.post("/api/v1/faces/verify")
async def verify_faces(request: VerifyRequest):
    """
    Verify if two faces are the same person
    Useful for re-verification or checking enrollment quality
    """
    try:
        result = face_service.verify_faces(request.image1, request.image2)
        
        return {
            "status": "success" if result['verified'] else "failed",
            "verified": result['verified'],
            "confidence": result['confidence'],
            "distance": result['distance'],
            "threshold": result['threshold'],
            "model": result['model']
        }
    except Exception as e:
        logger.error(f"Verification error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Additional utility endpoints

@app.get("/api/v1/faces/status", response_model=StatusResponse)
async def get_status():
    """Get API status and configuration"""
    model_info = face_service.get_model_info()
    
    try:
        users_data = laravel_sync.get_users_face_data()
        total_users = len(users_data) if users_data else 0
    except:
        total_users = 0
    
    return {
        "status": "operational",
        "service": "Face Recognition API (DeepFace)",
        "version": "2.0.0",
        "model": model_info['model_name'],
        "total_users": total_users,
        "face_threshold": config.FACE_MATCH_THRESHOLD
    }

@app.get("/api/v1/faces/model-info")
async def get_model_info():
    """Get detailed model information"""
    return face_service.get_model_info()

# Legacy endpoints (for backward compatibility)
@app.post("/api/faces/encode")
async def encode_face(request: IdentifyRequest):
    """Legacy endpoint for face encoding"""
    try:
        descriptor = face_service.extract_descriptor(request.image)
        return {
            "success": descriptor is not None,
            "encoding": descriptor,
            "dimensions": len(descriptor) if descriptor else 0,
            "error": None if descriptor else "No face detected"
        }
    except Exception as e:
        return {
            "success": False,
            "encoding": None,
            "error": str(e)
        }

@app.post("/api/faces/quality")
async def check_quality(request: QualityRequest):
    """Legacy endpoint for quality check"""
    return await assess_quality(request)

@app.post("/api/faces/identify")
async def identify_legacy(request: IdentifyRequest):
    """Legacy endpoint for identification"""
    return await identify_face(request)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    model_info = face_service.get_model_info()
    return {
        "name": "Face Recognition API (DeepFace)",
        "version": "2.0.0",
        "library": "deepface",
        "model": model_info['model_name'],
        "detector": model_info['detector_backend'],
        "endpoints": {
            "health": "/health",
            "register": "/api/v1/faces/register",
            "identify": "/api/v1/faces/identify",
            "quality": "/api/v1/faces/quality",
            "verify": "/api/v1/faces/verify",
            "status": "/api/v1/faces/status",
            "model_info": "/api/v1/faces/model-info"
        },
        "routes": {
            "data_user": "/data_user",
            "attendance": "/manual-attendance"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting Face Recognition API with DeepFace")
    logger.info(f"Model: {config.DEEPFACE_MODEL}")
    logger.info(f"Detector: {config.DEEPFACE_DETECTOR}")
    logger.info(f"Threshold: {config.FACE_MATCH_THRESHOLD}")
    
    uvicorn.run(
        app,
        host=config.HOST,
        port=config.PORT,
        log_level="info",
    )
