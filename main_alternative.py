from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import base64
import numpy as np
from deepface import DeepFace
import cv2
import io
from PIL import Image
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = "Facenet"
PRIMARY_DETECTOR = "opencv"
FALLBACK_DETECTOR = "mtcnn"
EMBEDDING_DIM = 128

app = FastAPI(title="Face Recognition API (DeepFace)", version="1.0.0")


class ImageData(BaseModel):
    image_data: str


class BatchImageData(BaseModel):
    images: list[str]


class HealthResponse(BaseModel):
    status: str
    message: str


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(status="success", message="DeepFace API is running")


@app.post("/api/faces/quality")
async def assess_quality(data: ImageData):
    try:
        image = decode_base64_image(data.image_data)
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image data")

        height, width = image.shape[:2]
        if height < 100 or width < 100:
            return {"quality": "poor", "score": 0.3, "feedback": "Image too small"}

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=4, minSize=(60, 60))

        if len(faces) == 0:
            return {"quality": "poor", "score": 0.3, "feedback": "Wajah tidak terdeteksi"}

        return {"quality": "good", "score": 0.9, "feedback": "Good quality image"}
    except Exception as e:
        logger.error(f"Quality assessment error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/faces/encode")
async def encode_face(data: ImageData):
    try:
        image = decode_base64_image(data.image_data)
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image data")

        # --- 1. Hybrid Face Detection & Liveness ---
        faces = None
        detector_used = PRIMARY_DETECTOR
        
        # Try Fast Detector First
        try:
            faces = DeepFace.extract_faces(
                image, 
                detector_backend=PRIMARY_DETECTOR, 
                anti_spoofing=True,
                enforce_detection=True
            )
        except Exception:
            # Fallback to Accurate Detector if no face found (usually due to hijab/glasses/low light)
            logger.info(f"Primary detector ({PRIMARY_DETECTOR}) failed, falling back to {FALLBACK_DETECTOR}")
            try:
                faces = DeepFace.extract_faces(
                    image, 
                    detector_backend=FALLBACK_DETECTOR, 
                    anti_spoofing=True,
                    enforce_detection=True
                )
                detector_used = FALLBACK_DETECTOR
            except Exception as e:
                logger.error(f"Fallback detector also failed: {e}")
                raise HTTPException(status_code=400, detail="Wajah tidak terdeteksi. Pastikan pencahayaan cukup dan wajah lurus ke kamera.")

        # Check Spoofing
        if faces and faces[0].get("is_spoof") is True:
            raise HTTPException(
                status_code=403, 
                detail="⚠️ Deteksi Spoofing: Wajah terdeteksi sebagai foto/layar HP. Harap gunakan wajah asli secara langsung."
            )

        # --- 2. Extract Embedding ---
        # We reuse the detector that already worked
        embedding = extract_embedding(image, detector_backend=detector_used)
        if embedding is None:
            raise HTTPException(status_code=400, detail="Gagal mengekstrak fitur wajah.")

        return {
            "success": True,
            "encoding": embedding,
            "detector": detector_used,
            "location": {"top": 0, "right": 100, "bottom": 100, "left": 0},
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Face encoding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/faces/encode-batch")
async def encode_face_batch(data: BatchImageData):
    try:
        embeddings = []
        failed = 0
        spoofs = 0

        for idx, image_data in enumerate(data.images):
            image = decode_base64_image(image_data)
            if image is None:
                failed += 1
                continue

            # In batch (registration), we can be a bit more lenient or choose to stick with one
            # To ensure registration quality, we use the hybrid check too
            try:
                # Try Fast First
                try:
                    res = DeepFace.extract_faces(image, detector_backend=PRIMARY_DETECTOR, anti_spoofing=True)
                    detector = PRIMARY_DETECTOR
                except Exception:
                    res = DeepFace.extract_faces(image, detector_backend=FALLBACK_DETECTOR, anti_spoofing=True)
                    detector = FALLBACK_DETECTOR
                
                if res and res[0].get("is_spoof") is True:
                    spoofs += 1
                    continue
                
                embedding = extract_embedding(image, detector_backend=detector)
                if embedding:
                    embeddings.append(embedding)
                else:
                    failed += 1
            except Exception:
                failed += 1

        if len(embeddings) == 0 and spoofs > 0:
            raise HTTPException(status_code=403, detail="Semua foto terdeteksi sebagai spoofing/palsu.")

        return {
            "success": True,
            "encodings": embeddings,
            "total": len(embeddings),
            "failed": failed,
            "spoofs": spoofs,
            "embedding_dim": EMBEDDING_DIM,
            "model": MODEL_NAME,
        }
    except Exception as e:
        logger.error(f"Batch encoding error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def extract_embedding(image, detector_backend=PRIMARY_DETECTOR):
    """Extract face embedding using the verified detector. Normalizes to L2."""
    embedding = None
    try:
        result = DeepFace.represent(
            image, 
            model_name=MODEL_NAME, 
            detector_backend=detector_backend,
            enforce_detection=True
        )
        if result and len(result) > 0:
            embedding = result[0]["embedding"]
    except Exception:
        # Lenient fallback
        try:
            result = DeepFace.represent(
                image, 
                model_name=MODEL_NAME, 
                detector_backend=detector_backend,
                enforce_detection=False
            )
            if result and len(result) > 0:
                embedding = result[0]["embedding"]
        except Exception:
            pass

    if embedding is not None:
        emb_arr = np.array(embedding)
        norm = np.linalg.norm(emb_arr)
        if norm > 0:
            return (emb_arr / norm).tolist()
        return embedding
    return None


def decode_base64_image(image_data: str):
    try:
        if "base64," in image_data:
            image_data = image_data.split("base64,")[1]
        image_bytes = base64.b64decode(image_data)
        image = Image.open(io.BytesIO(image_bytes))
        if image.mode == "RGBA":
            image = image.convert("RGB")
        return cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
    except Exception as e:
        logger.error(f"Image decoding error: {e}")
        return None


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Face Recognition API with DeepFace...")
    print("📍 API will be available at: http://localhost:8000")
    print("📖 API Documentation at: http://localhost:8000/docs")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
