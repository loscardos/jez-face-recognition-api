# Face Recognition API - DeepFace Implementation v2.0

Python FastAPI backend untuk face recognition dan attendance management. Menggunakan **DeepFace library** dengan model **FaceNet/ArcFace** untuk akurasi tinggi dan support 200+ users.

## 🆕 What's New in v2.0

- **DeepFace Integration**: Menggunakan model deep learning (FaceNet/ArcFace) untuk akurasi lebih tinggi
- **200+ Users Support**: Optimized untuk dataset besar dengan matching algorithm yang efisien
- **Better Variation Handling**: Lebih toleran terhadap variasi pose, pencahayaan, dan accessories
- **Pre-download Models**: Model di-download sekali, digunakan berkali-kali
- **Top-K Matching**: Menggunakan rata-rata top-3 similarity untuk matching yang lebih akurat

## Architecture

```
React Native App       Laravel Backend       Python Backend (DeepFace)
  (Camera)    <--->   (API Routes)   <--->  (Face Recognition)
       |                      |                      |
       |                      |               FaceNet/ArcFace
       |                      |               128/512-d Embedding
       |                      |               Cosine Similarity
       |                      |
  /data_user           /manual-attendance
  (Registration)       (Identification)
```

## Features

- **Face Encoding**: DeepFace embedding (128-d Facenet atau 512-d ArcFace)
- **Face Matching**: Cosine similarity dengan top-K averaging
- **Quality Assessment**: Sharpness detection dan face ratio validation
- **Multi-pose Registration**: Support 5-20 samples per user
- **Face Verification**: Bandingkan 2 wajah untuk re-verification
- **Model Caching**: Load model sekali, reuse untuk semua request

## Requirements

- Python 3.8+
- RAM: 4GB minimum (8GB recommended)
- Disk: ~500MB untuk models
- CPU: Multi-core recommended untuk 200+ users

## Setup

### 1. Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Download Models (Pre-download)

```bash
# Download model sekali, hindari download saat runtime
python download_models.py
```

Model yang akan di-download:
- FaceNet: ~90 MB
- RetinaFace (optional): ~100 MB

### 3. Configure Environment

Copy `.env.example` ke `.env` dan sesuaikan:

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Laravel Backend
LARAVEL_API_URL=http://localhost:8000/api

# DeepFace Configuration
DEEPFACE_MODEL=Facenet          # Options: Facenet, ArcFace, VGG-Face
DEEPFACE_DETECTOR=opencv        # Options: opencv, retinaface, mtcnn
FACE_MATCH_THRESHOLD=0.65       # Cosine similarity threshold
```

### 4. Run Server

```bash
python main.py
```

Server akan start di `http://localhost:8000`

## API Endpoints

### Health Check
```bash
GET /health
```

### Face Registration (untuk /data_user)
```bash
POST /api/v1/faces/register
Body: {
  "images": ["data:image/jpeg;base64,...", "..."],  # 5-20 images
  "user_id": 123
}

Response: {
  "status": "success",
  "message": "Wajah berhasil didaftar dengan 10 template",
  "data": {
    "registered": true,
    "descriptor_count": 10,
    "descriptors": [[...], [...]],  # DeepFace embeddings
    "model": "Facenet",
    "processing_time": 2.34
  }
}
```

### Face Identification (untuk /manual-attendance)
```bash
POST /api/v1/faces/identify
Body: {
  "image": "data:image/jpeg;base64,...",
  "location": {"lat": -6.2, "lng": 106.8},
  "metadata": {"device": "mobile", "timestamp": "..."}
}

Response: {
  "status": "success",
  "message": "Wajah berhasil dikenali.",
  "data": {
    "user": {
      "id": 123,
      "name": "John Doe",
      "email": "john@example.com"
    },
    "match": {
      "confidence": 0.89,
      "distance": 0.11,
      "threshold": 0.65
    },
    "processing_time": 0.85
  }
}
```

### Quality Assessment
```bash
POST /api/v1/faces/quality
Body: {
  "image": "data:image/jpeg;base64,..."
}

Response: {
  "status": "good",
  "score": 0.92,
  "is_acceptable": true,
  "feedback": "Kualitas wajah baik",
  "details": {
    "face_ratio": 0.25,
    "sharpness": 245.3,
    "confidence": 0.99
  }
}
```

### Face Verification (Compare 2 faces)
```bash
POST /api/v1/faces/verify
Body: {
  "image1": "data:image/jpeg;base64,...",
  "image2": "data:image/jpeg;base64,..."
}

Response: {
  "status": "success",
  "verified": true,
  "confidence": 0.92,
  "distance": 0.08,
  "threshold": 0.65
}
```

### Status & Info
```bash
GET /api/v1/faces/status
GET /api/v1/faces/model-info
GET /
```

## Configuration Guide

### Model Selection

| Model | Accuracy | Speed | Size | Recommendation |
|-------|----------|-------|------|----------------|
| **Facenet** | ⭐⭐⭐⭐ | ⚡⚡⚡⚡ | ~90MB | **Default untuk 200 users** |
| ArcFace | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | ~130MB | Higher accuracy, slightly slower |
| VGG-Face | ⭐⭐⭐⭐ | ⚡⚡ | ~500MB | Too heavy for this use case |

### Detector Selection

| Detector | Accuracy | Speed | Recommendation |
|----------|----------|-------|----------------|
| **opencv** | ⭐⭐⭐ | ⚡⚡⚡⚡ | **Default - fastest** |
| retinaface | ⭐⭐⭐⭐⭐ | ⚡⚡⚡ | Best for angles, slightly slower |
| mtcnn | ⭐⭐⭐⭐ | ⚡⚡ | Good but slower |

### Threshold Tuning

- **Facenet**: 0.60-0.70 (default: 0.65)
- **ArcFace**: 0.50-0.60

**Terlalu banyak false negative?** → Turunkan threshold 0.02-0.05
**Terlalu banyak false positive?** → Naikkan threshold 0.02-0.05

## Performance Benchmarks

### With FaceNet + OpenCV (Recommended)

| Metric | Value |
|--------|-------|
| Model Load Time | ~3-5 seconds |
| Single Face Encoding | ~0.5-1.0 seconds |
| Matching 200 Users | ~0.1-0.3 seconds |
| Memory Usage | ~400-600 MB |
| Concurrent Requests | 10-20/second |

## Troubleshooting

### Model Download Failed
```bash
# Pre-download manual
python download_models.py

# Check cache directory
ls -la .deepface/
```

### Low Accuracy
1. **Periksa threshold**: Sesuaikan `FACE_MATCH_THRESHOLD`
2. **Daftar ulang**: User dengan variasi besar perlu re-registration
3. **Pencahayaan**: Pastikan cahaya merata saat registrasi

### Memory Issues
1. Gunakan model `Facenet` (lebih ringan dari ArcFace)
2. Gunakan detector `opencv` (lebih ringan dari retinaface)
3. Pastikan tidak ada memory leak di Laravel integration

### Face Not Detected
1. Periksa kualitas gambar (resolution, blur)
2. Coba detector `retinaface` untuk deteksi lebih baik
3. Pastikan wajah menghadap ke depan (frontal)

## Migration from v1.0 (OpenCV)

Jika Anda upgrade dari versi OpenCV:

1. **Backup data**: `users.u_face` masih kompatibel
2. **Update .env**: Tambahkan konfigurasi DeepFace
3. **Download models**: `python download_models.py`
4. **Test**: Lakukan test dengan beberapa user dulu
5. **Re-registration** (optional): Untuk akurasi optimal, re-register user dengan DeepFace

## Integration dengan Laravel

Pastikan Laravel backend mengirimkan data dalam format:

```json
{
  "u_face": {
    "samples": [[...embedding...], [...embedding...]],
    "model": "Facenet",
    "registered_at": "2024-01-15T10:30:00Z"
  }
}
```

Laravel endpoints yang digunakan:
- `GET /api/v1/admin/face-data/all` - Get all users' face data
- `GET /api/v1/mobile/face` - Get user's face data
- `POST /api/v1/mobile/face` - Store face encoding
- `GET /api/v1/admin/users/{id}` - Get user details

## File Structure

```
face-attendance-ai/
├── main.py                      # FastAPI application
├── face_recognition_service.py  # DeepFace implementation
├── laravel_sync.py             # Laravel integration
├── config.py                   # Configuration
├── download_models.py          # Pre-download script
├── requirements.txt            # Dependencies
├── .env.example               # Environment template
├── .deepface/                 # Model cache directory
│   └── weights/
│       ├── facenet_weights.h5
│       └── ...
└── logs/                      # Log files
```

## Checkpoint

Jika Anda ingin rollback ke versi sebelumnya, backup tersedia di:
```
face-attendance-ai-backup-YYYYMMDD_HHMMSS/
```

## License

MIT License - Internal Use Only
