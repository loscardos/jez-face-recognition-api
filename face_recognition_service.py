"""
Face Recognition Service - DeepFace Implementation
Handles face detection, encoding, and matching using DeepFace library
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from PIL import Image
import io
import base64
import json
import os
import logging
from deepface import DeepFace
from functools import lru_cache
import hashlib

from config import config

logger = logging.getLogger(__name__)

class FaceRecognitionService:
    """Service for face recognition and matching using DeepFace"""

    def __init__(self):
        self.threshold = config.FACE_MATCH_THRESHOLD
        self.model_name = config.DEEPFACE_MODEL
        self.detector_backend = config.DEEPFACE_DETECTOR
        
        # Model cache - load once, reuse many times
        self._model = None
        self._model_loaded = False
        
        # Pre-download and cache model
        self._preload_model()

    def _preload_model(self):
        """Preload model untuk performa lebih baik"""
        try:
            logger.info(f"Preloading DeepFace model: {self.model_name}")
            self._model = DeepFace.build_model(self.model_name)
            self._model_loaded = True
            logger.info(f"Model {self.model_name} loaded successfully")
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            self._model_loaded = False

    def _base64_to_image(self, base64_data: str) -> np.ndarray:
        """Convert base64 string to OpenCV image"""
        # Remove data:image/png;base64, prefix if present
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]
        
        image_bytes = base64.b64decode(base64_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        return image

    def _image_to_base64(self, image: np.ndarray) -> str:
        """Convert OpenCV image to base64 string"""
        _, buffer = cv2.imencode('.jpg', image)
        base64_str = base64.b64encode(buffer).decode('utf-8')
        return f"data:image/jpeg;base64,{base64_str}"

    def encode_face_from_image(self, image_data: bytes) -> Optional[Dict]:
        """
        Encode face from image bytes using DeepFace
        Returns: dict dengan embedding dan face location
        """
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return None

            # Save to temp file for DeepFace (DeepFace butuh file path atau array)
            temp_path = "/tmp/temp_face.jpg"
            cv2.imwrite(temp_path, image)

            # Extract embedding dengan DeepFace
            embeddings = DeepFace.represent(
                img_path=temp_path,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                enforce_detection=True,
                align=True  # Align wajah untuk konsistensi
            )

            if not embeddings or len(embeddings) == 0:
                return None

            # Ambil embedding pertama (jika multiple faces, ambil yang terbesar)
            if len(embeddings) > 1:
                # Pilih wajah dengan area terbesar
                best_face = max(embeddings, key=lambda x: x.get('facial_area', {}).get('w', 0) * x.get('facial_area', {}).get('h', 0))
            else:
                best_face = embeddings[0]

            facial_area = best_face.get('facial_area', {})
            
            return {
                'encoding': best_face['embedding'],  # 128-d atau 512-d embedding
                'location': {
                    'top': int(facial_area.get('y', 0)),
                    'right': int(facial_area.get('x', 0) + facial_area.get('w', 0)),
                    'bottom': int(facial_area.get('y', 0) + facial_area.get('h', 0)),
                    'left': int(facial_area.get('x', 0))
                },
                'confidence': float(best_face.get('confidence', 0.99)),
                'model': self.model_name
            }

        except Exception as e:
            logger.error(f"Error encoding face with DeepFace: {str(e)}")
            return None
        finally:
            # Cleanup temp file
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass

    def encode_face_from_base64(self, base64_data: str) -> Optional[Dict]:
        """
        Encode face from base64 image data
        """
        try:
            if ',' in base64_data:
                base64_data = base64_data.split(',')[1]
            
            image_data = base64.b64decode(base64_data)
            return self.encode_face_from_image(image_data)
        except Exception as e:
            logger.error(f"Error decoding base64 image: {str(e)}")
            return None

    def extract_descriptor(self, base64_image: str) -> Optional[List[float]]:
        """
        Extract single face descriptor from base64 image
        Used for identification
        """
        result = self.encode_face_from_base64(base64_image)
        return result['encoding'] if result else None

    def extract_multiple_descriptors(self, base64_images: List[str]) -> List[List[float]]:
        """
        Extract face descriptors from multiple base64 images
        Used for registration - returns list of descriptors
        """
        descriptors = []
        
        for idx, image in enumerate(base64_images):
            try:
                descriptor = self.extract_descriptor(image)
                if descriptor:
                    descriptors.append(descriptor)
                    logger.info(f"Successfully extracted descriptor {idx+1}/{len(base64_images)}")
                else:
                    logger.warning(f"Failed to extract descriptor {idx+1}/{len(base64_images)}")
            except Exception as e:
                logger.error(f"Error extracting descriptor {idx+1}: {e}")
                continue

        return descriptors

    def assess_quality(self, base64_image: str) -> Dict:
        """
        Assess quality of face image for registration
        Returns Laravel-compatible response dengan analisis lebih detail
        """
        try:
            # Decode base64
            if ',' in base64_image:
                base64_image = base64_image.split(',')[1]

            image_data = base64.b64decode(base64_image)
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return {
                    'status': 'error',
                    'score': 0.0,
                    'is_acceptable': False,
                    'feedback': 'Invalid image data'
                }

            height, width = image.shape[:2]
            
            # Save temp untuk DeepFace detection
            temp_path = "/tmp/temp_quality.jpg"
            cv2.imwrite(temp_path, image)

            try:
                # Deteksi wajah dengan DeepFace
                embeddings = DeepFace.represent(
                    img_path=temp_path,
                    model_name=self.model_name,
                    detector_backend=self.detector_backend,
                    enforce_detection=True,
                    align=True
                )
            except Exception as e:
                if "Face could not be detected" in str(e):
                    return {
                        'status': 'error',
                        'score': 0.0,
                        'is_acceptable': False,
                        'feedback': 'Tidak ada wajah terdeteksi dalam gambar. Pastikan wajah terlihat jelas.'
                    }
                raise e
            finally:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except:
                        pass

            if len(embeddings) == 0:
                return {
                    'status': 'error',
                    'score': 0.0,
                    'is_acceptable': False,
                    'feedback': 'Tidak ada wajah terdeteksi dalam gambar'
                }

            if len(embeddings) > 1:
                return {
                    'status': 'error',
                    'score': 0.5,
                    'is_acceptable': False,
                    'feedback': f'{len(embeddings)} wajah terdeteksi. Pastikan hanya satu wajah dalam frame.'
                }

            face = embeddings[0]
            facial_area = face.get('facial_area', {})
            face_width = facial_area.get('w', 0)
            face_height = facial_area.get('h', 0)
            
            # Hitung rasio wajah terhadap gambar
            face_size_ratio = (face_width * face_height) / (width * height)

            # Analisis kualitas gambar
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()  # Sharpness
            
            # Feedback berdasarkan kondisi
            feedback = []
            
            if face_size_ratio < 0.05:
                return {
                    'status': 'poor',
                    'score': 0.3,
                    'is_acceptable': False,
                    'feedback': 'Wajah terlalu kecil. Silakan mendekat ke kamera.',
                    'details': {'face_ratio': face_size_ratio, 'sharpness': laplacian_var}
                }

            if face_size_ratio > 0.8:
                return {
                    'status': 'poor',
                    'score': 0.3,
                    'is_acceptable': False,
                    'feedback': 'Wajah terlalu besar. Silakan menjauh sedikit dari kamera.',
                    'details': {'face_ratio': face_size_ratio, 'sharpness': laplacian_var}
                }

            if laplacian_var < 100:
                feedback.append('Gambar kurang fokus.')
            
            # Hitung score berdasarkan beberapa faktor
            score = min(1.0, face.get('confidence', 0.99))
            
            # Adjust score berdasarkan ukuran dan sharpness
            if face_size_ratio < 0.1:
                score *= 0.8
            if laplacian_var < 100:
                score *= 0.9

            return {
                'status': 'good' if score > 0.8 else 'fair',
                'score': round(score, 2),
                'is_acceptable': score > 0.7,
                'feedback': 'Kualitas wajah baik' if not feedback else ' '.join(feedback),
                'details': {
                    'face_ratio': round(face_size_ratio, 3),
                    'sharpness': round(laplacian_var, 2),
                    'confidence': round(face.get('confidence', 0.99), 3)
                }
            }

        except Exception as e:
            logger.error(f"Error assessing face quality: {str(e)}")
            return {
                'status': 'error',
                'score': 0.0,
                'is_acceptable': False,
                'feedback': f'Error: {str(e)}'
            }

    def find_matching_user(self, descriptor: List[float], users_face_data: Dict[int, Dict]) -> Dict:
        """
        Find matching user from face descriptor menggunakan cosine similarity
        users_face_data: {user_id: {'samples': [[...], [...]], ...}}
        Returns: {'matched': bool, 'user_id': int, 'distance': float, 'confidence': float}
        """
        best_match = {
            'matched': False,
            'user_id': None,
            'distance': float('inf'),
            'confidence': 0.0
        }

        test_encoding = np.array(descriptor)
        
        logger.info(f"Matching against {len(users_face_data)} users")

        for user_id, user_data in users_face_data.items():
            samples = user_data.get('samples', [])
            if not samples:
                continue

            # Hitung similarity dengan semua sampel user ini
            similarities = []
            for sample in samples:
                try:
                    stored_encoding = np.array(sample)
                    
                    # Cosine similarity
                    dot_product = np.dot(test_encoding, stored_encoding)
                    norm_test = np.linalg.norm(test_encoding)
                    norm_stored = np.linalg.norm(stored_encoding)
                    
                    if norm_test == 0 or norm_stored == 0:
                        continue
                        
                    cosine_sim = dot_product / (norm_test * norm_stored)
                    similarities.append(cosine_sim)
                except Exception as e:
                    logger.error(f"Error calculating similarity: {e}")
                    continue

            if not similarities:
                continue

            # Gunakan rata-rata top-k similarities
            top_k = min(3, len(similarities))
            top_similarities = sorted(similarities, reverse=True)[:top_k]
            avg_similarity = np.mean(top_similarities)
            
            # Convert to distance (0 = same, 2 = opposite)
            distance = 1.0 - avg_similarity

            # Check if this is a better match
            if distance < best_match['distance']:
                confidence = max(0.0, avg_similarity)
                # Gunakan distance threshold: distance harus < (1 - threshold)
                # Facenet512: threshold 0.35 berarti distance harus < 0.65
                # Tapi juga butuh confidence minimum absolut
                distance_threshold = 1.0 - self.threshold
                matched = distance < distance_threshold and confidence >= 0.70

                best_match = {
                    'matched': matched,
                    'user_id': user_id,
                    'distance': float(distance),
                    'confidence': float(confidence),
                    'matches_count': len(similarities)
                }
                
                logger.info(f"User {user_id}: confidence={confidence:.3f}, distance={distance:.3f}, matched={matched}")

        return best_match

    def verify_faces(self, base64_image1: str, base64_image2: str) -> Dict:
        """
        Verifikasi apakah dua wajah adalah orang yang sama
        Untuk validasi enrollment atau re-verification
        """
        try:
            # Decode images
            img1 = self._base64_to_image(base64_image1)
            img2 = self._base64_to_image(base64_image2)
            
            # Save temp files
            temp1 = "/tmp/verify_1.jpg"
            temp2 = "/tmp/verify_2.jpg"
            cv2.imwrite(temp1, img1)
            cv2.imwrite(temp2, img2)
            
            # Verify dengan DeepFace
            result = DeepFace.verify(
                img1_path=temp1,
                img2_path=temp2,
                model_name=self.model_name,
                detector_backend=self.detector_backend,
                distance_metric="cosine",
                enforce_detection=True
            )
            
            # Cleanup
            for f in [temp1, temp2]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass
            
            return {
                'verified': result['verified'],
                'distance': result['distance'],
                'threshold': result['threshold'],
                'confidence': 1.0 - result['distance'],
                'model': self.model_name
            }
            
        except Exception as e:
            logger.error(f"Error verifying faces: {e}")
            return {
                'verified': False,
                'distance': 1.0,
                'confidence': 0.0,
                'error': str(e)
            }
        finally:
            # Cleanup
            for f in ["/tmp/verify_1.jpg", "/tmp/verify_2.jpg"]:
                if os.path.exists(f):
                    try:
                        os.remove(f)
                    except:
                        pass

    def get_model_info(self) -> Dict:
        """Get current model information"""
        return {
            'model_name': self.model_name,
            'detector_backend': self.detector_backend,
            'threshold': self.threshold,
            'loaded': self._model_loaded,
            'embedding_dim': 128 if 'FaceNet' in self.model_name else 512
        }

# Global service instance
face_service = FaceRecognitionService()
