# Summary Solusi Face Recognition Attendance JEZ

> Status update: DeepFace/TensorFlow support has now been removed from this service. The active runtime path is InsightFace `buffalo_m` + ONNXRuntime + cached/vectorized matching. Sections below that describe DeepFace are historical context for why the migration was needed.

## Problem Saat Ini

Repo `jez-face-recognition-api` saat ini lambat dan tidak akurat karena pipeline-nya terlalu berat dan kurang aman untuk production.

Masalah utama:

```text
1. Image dikirim sebagai Base64 JSON
2. Backend decode image lalu tulis ke temp file
3. DeepFace melakukan full pipeline setiap request
4. FastAPI fetch semua face data dari Laravel setiap absen
5. JSON descriptor besar di-parse ulang
6. Matching dilakukan brute-force
7. Confidence hanya similarity, bukan probabilitas valid
8. Tidak ada top-2 margin check
9. Akibatnya bisa match ke user salah walau confidence 74%
```

Target absensi yang bagus:

```text
Ideal: ≤ 1.5 detik
Acceptable: 1.5 - 2.5 detik
Lambat: > 3 detik
Problem serius: > 5 detik
```

---

# Solusi Utama

## Gunakan Pipeline Laravel + FastAPI + InsightFace

InsightFace lebih cocok dibanding implementasi DeepFace sekarang karena:

```text
1. Lebih production-oriented untuk face detection, alignment, dan recognition
2. Pakai ONNXRuntime, lebih ringan untuk inference di VPS CPU
3. Output embedding lebih direct untuk vector matching
4. Lebih mudah dibuat cached dan vectorized
5. Lebih mudah menerapkan top-k + margin check
6. Cocok dipisah sebagai microservice FastAPI
```

---

# Arsitektur yang Disarankan

```text
Mobile / Web Attendance
        ↓
Laravel API
- auth
- validasi user
- validasi shift
- validasi branch/lokasi
- business rule absensi
- simpan attendance log
        ↓ internal only
FastAPI Face Recognition Service
- receive image
- detect face
- generate embedding
- match ke cache template
- return kandidat + score
        ↓
Database
- users
- user_face_templates
- attendance_logs
- face_match_audits
```

Laravel tetap menjadi **business brain**.
FastAPI hanya menjadi **face identity engine**.

---

# Model InsightFace yang Direkomendasikan

## Pilihan utama

```text
Model pack: buffalo_m
Provider: CPUExecutionProvider
det_size awal: 640x640
```

Alasan:

```text
1. Lebih ringan dari buffalo_l
2. Akurasi recognition tetap sangat tinggi
3. Cocok untuk VPS CPU-only
4. Balance antara speed dan akurasi
```

## Alternatif

| Model       | Kapan dipakai                                         |
| ----------- | ----------------------------------------------------- |
| `buffalo_m` | pilihan utama, balance speed + accuracy               |
| `buffalo_l` | benchmark akurasi terbaik                             |
| `buffalo_s` | fallback kalau butuh sangat cepat, tapi akurasi turun |

Untuk case JEZ, jangan mulai dari `buffalo_s` karena sebelumnya sudah ada problem salah nama.

---

# Flow Absensi Baru

```text
1. User buka kamera
2. Frontend ambil 1 frame terbaik
3. Kirim image ke Laravel / langsung ke FastAPI internal via Laravel
4. FastAPI detect wajah dengan InsightFace
5. FastAPI generate embedding
6. FastAPI compare embedding ke cache matrix
7. FastAPI return top candidate
8. Laravel validasi business rule
9. Laravel simpan absensi
```

---

# Flow Register Wajah

```text
1. User didaftarkan dengan 5-10 sample wajah
2. Setiap image dicek kualitasnya
3. FastAPI generate embedding per sample
4. Semua sample dicek konsistensinya
5. Jika sample terlalu beda, reject registration
6. Simpan embedding ke table user_face_templates
7. Reload cache FastAPI
```

---

# Struktur Table yang Disarankan

Jangan simpan face embedding di `users.u_face`.

Gunakan table khusus:

```sql
CREATE TABLE user_face_templates (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    detector_name VARCHAR(50) NULL,
    embedding JSON NOT NULL,
    quality_score DECIMAL(5,2) NULL,
    sample_index INT DEFAULT 1,
    is_active TINYINT DEFAULT 1,
    created_at TIMESTAMP NULL,
    updated_at TIMESTAMP NULL
);
```

Opsional audit:

```sql
CREATE TABLE face_match_audits (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NULL,
    matched_user_id BIGINT NULL,
    status VARCHAR(50),
    best_score DECIMAL(8,6),
    second_score DECIMAL(8,6),
    margin DECIMAL(8,6),
    model_name VARCHAR(50),
    processing_ms INT,
    created_at TIMESTAMP NULL
);
```

---

# Matching Logic yang Aman

Jangan pakai logic:

```text
ambil score tertinggi
kalau di atas threshold → success
```

Gunakan:

```text
best_score harus tinggi
DAN
best_score - second_score harus cukup jauh
```

Contoh rule awal:

```python
AUTO_MATCH_THRESHOLD = 0.45
AMBIGUOUS_THRESHOLD = 0.38
MIN_MARGIN = 0.05
```

Decision:

```text
best_score >= 0.45 dan margin >= 0.05
= matched

best_score >= 0.38 tapi margin kecil
= ambiguous / retry

best_score < 0.38
= not found
```

Threshold wajib dikalibrasi pakai data asli karyawan JEZ.

---

# Contoh Response FastAPI

```json
{
  "status": "matched",
  "user_id": 123,
  "score": 0.52,
  "second_score": 0.39,
  "margin": 0.13,
  "model": "buffalo_m",
  "processing_ms": 820
}
```

Kalau ambigu:

```json
{
  "status": "ambiguous",
  "best_candidate": 123,
  "best_score": 0.44,
  "second_candidate": 88,
  "second_score": 0.42,
  "margin": 0.02,
  "message": "Wajah mirip dengan lebih dari satu user. Silakan ulangi scan."
}
```

---

# Optimasi Speed Wajib

## 1. Cache face template di FastAPI

Saat service start:

```text
- load semua active face templates dari Laravel/DB
- convert ke NumPy matrix
- simpan user_id mapping
```

Saat absen:

```text
- generate embedding input
- scores = FACE_MATRIX @ input_embedding
- ambil top-3 candidate
```

Matching harusnya hanya:

```text
5 - 50 ms
```

Bukan 6 detik.

---

## 2. Jangan fetch Laravel setiap request

Hindari flow ini:

```text
Absensi masuk
→ FastAPI call Laravel get all face data
→ parse JSON besar
→ matching
```

Ganti dengan:

```text
Absensi masuk
→ match ke cache memory
```

Jika ada update face:

```text
Laravel → call FastAPI /reload-cache
```

---

## 3. Jangan pakai Base64 JSON

Status implementasi saat ini: endpoint face image aktif sudah menggunakan `multipart/form-data` dan implementasi Base64 legacy sudah dihapus dari service ini.

Hindari:

```json
{
  "image": "data:image/jpeg;base64,..."
}
```

Gunakan:

```text
multipart/form-data
image=@face.jpg
```

Lebih ringan:

* payload lebih kecil,
* parsing lebih cepat,
* memory lebih hemat.

---

## 4. Hindari temp file statis

Jangan pakai:

```python
/tmp/temp_face.jpg
```

Karena rawan bentrok antar request.

Lebih baik:

* proses langsung dari bytes/NumPy array,
* atau gunakan unique temp file jika benar-benar perlu.

---

## 5. Resize image sebelum recognition

Untuk attendance:

```text
max width: 640 - 960 px
```

Kalau frontend bisa crop wajah:

```text
face crop: 224 - 320 px
```

Jangan kirim foto kamera full resolution 2-5 MB ke backend.

---

# Estimasi Speed Setelah Pipeline Baru

Dengan VPS kamu:

```text
20 vCPU / 24 GB RAM
```

Target realistis:

| Tahap                          |       Estimasi |
| ------------------------------ | -------------: |
| Upload image kecil             |    50 - 200 ms |
| Decode image                   |    20 - 100 ms |
| InsightFace detect + embedding | 300 ms - 1.5 s |
| Vector matching cached         |      5 - 50 ms |
| Laravel save attendance        |    50 - 300 ms |
| Total target                   |    0.5 - 2.0 s |

Kalau masih di atas 4 detik, kemungkinan problem ada di:

* image terlalu besar,
* model reload per request,
* fetch Laravel setiap request,
* ONNXRuntime thread belum optimal,
* worker terlalu banyak/terlalu sedikit,
* matching belum vectorized.

---

# Security Deployment

FastAPI face service jangan public.

Gunakan:

```text
Laravel public
FastAPI private/internal only
```

Opsi:

```text
1. Bind FastAPI ke 127.0.0.1
2. Atau Docker internal network
3. Atau private subnet
4. Tambahkan internal API token
5. Batasi CORS
6. Jangan expose endpoint face recognition ke internet
```

Contoh header internal:

```http
X-Internal-Token: <secret>
```

---

# Production Checklist

## P0 - Wajib sebelum production

```text
[ ] Ganti DeepFace flow ke InsightFace FastAPI service
[ ] Gunakan buffalo_m
[ ] Re-enroll semua wajah
[ ] Jangan campur embedding DeepFace lama dengan InsightFace
[ ] Buat table user_face_templates
[ ] Cache embedding di memory
[ ] Tambah /reload-cache endpoint
[ ] Ganti Base64 ke multipart upload
[ ] Implement top-k + margin check
[ ] FastAPI hanya internal/private
[ ] Tambah API token antar service
[ ] Log audit match tanpa menyimpan image mentah
```

## P1 - Setelah pilot stabil

```text
[ ] Tambah quality check saat enrollment
[ ] Tambah duplicate face detection saat registrasi
[ ] Tambah ambiguous retry flow
[ ] Tambah dashboard audit false positive/false negative
[ ] Benchmark threshold dari data real kantor
[ ] Tambah rate limit
[ ] Tambah monitoring latency per tahap
```

## P2 - Scale lebih besar

```text
[ ] FAISS jika template sudah ribuan/banyak cabang
[ ] pgvector/Qdrant jika butuh search terdistribusi
[ ] Multi-worker FastAPI dengan warm model
[ ] Frontend face detection/crop pakai MediaPipe
[ ] Liveness detection / anti-spoofing
```

---

# Final Recommendation

Solusi terbaik untuk case JEZ:

```text
Laravel tetap handle attendance business logic.
FastAPI dibuat ulang sebagai dedicated InsightFace service.
Gunakan buffalo_m sebagai model utama.
Simpan embedding di table khusus.
Cache semua template di memory.
Matching pakai NumPy matrix.
Decision pakai threshold + top-2 margin.
Jangan percaya confidence mentah.
Jangan fetch semua user dari Laravel setiap absensi.
```

Target akhir:

```text
Latency: 0.5 - 2 detik
False positive: ditekan dengan margin check
False negative: ditangani dengan retry/ambiguous flow
Architecture: clean Laravel + FastAPI microservice
```
