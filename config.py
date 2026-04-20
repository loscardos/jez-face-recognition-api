import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # FastAPI
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 8000))
    DEBUG = os.getenv('DEBUG', 'true').lower() == 'true'
    
    # Database Config
    DATABASE_NAME = 'jez_erp'
    USERS_TABLE = 'users'
    FACE_COLUMN = 'u_face'
    
    # Laravel Backend
    LARAVEL_API_URL = os.getenv('LARAVEL_API_URL', 'http://localhost:8000/api')
    
    # Face Recognition - DeepFace Settings
    # Model options: "Facenet", "Facenet512", "ArcFace", "VGG-Face", "OpenFace"
    DEEPFACE_MODEL = os.getenv('DEEPFACE_MODEL', 'Facenet')
    
    # Detector options: "opencv", "retinaface", "mtcnn", "ssd", "dlib"
    DEEPFACE_DETECTOR = os.getenv('DEEPFACE_DETECTOR', 'opencv')
    
    # Match threshold (cosine similarity, 0-1, higher = stricter)
    # Facenet recommended: 0.6-0.7
    # ArcFace recommended: 0.5-0.6
    FACE_MATCH_THRESHOLD = float(os.getenv('FACE_MATCH_THRESHOLD', 0.65))
    
    # Minimum confidence for face detection
    MIN_DETECTION_CONFIDENCE = float(os.getenv('MIN_DETECTION_CONFIDENCE', 0.8))
    
    # Storage
    FACE_DATA_DIR = os.path.join(os.path.dirname(__file__), 'face_data')
    LOGS_DIR = os.path.join(os.path.dirname(__file__), 'logs')
    
    # Model cache directory
    DEEPFACE_HOME = os.getenv('DEEPFACE_HOME', os.path.join(os.path.dirname(__file__), '.deepface'))
    os.environ['DEEPFACE_HOME'] = DEEPFACE_HOME
    
    # Ensure directories exist
    os.makedirs(FACE_DATA_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)
    os.makedirs(DEEPFACE_HOME, exist_ok=True)

config = Config()
