# FACE REGISTRATION WORKFLOW - COMPLETE SUMMARY

Dokumen ini memberikan penjelasan lengkap tentang bagaimana sistem registrasi wajah bekerja dari A sampai Z.

---

## 🎯 Pertanyaan: "Pendaftaran wajahnya konsepnya nanti bagaimana ya?"

### Jawaban Singkat:
1. **Registrasi** (sekali saja): PIC ambil foto karyawan 10x dari sudut berbeda → Upload → Simpan di database
2. **Penggunaan Harian** (setiap hari): Karyawan ambil foto 1x saat absen → Cocok dengan 10 foto yang sudah disimpan → Record attendance

### Ringkas: 
- **Fase Setup**: 10+ foto disimpan per karyawan
- **Fase Harian**: 1 foto dicocokkan dengan 10 yang disimpan

---

## 📊 Diagram Alur Lengkap

### Fase 1: REGISTRASI (Initialization)

```
┌─────────────────────────────────────────────────────┐
│          REACT NATIVE APP (PIC/Admin)               │
│                                                     │
│ 1. Login dengan credentials                        │
│ 2. Select menu "Register User Faces"              │
│ 3. Search and select karyawan                      │
│ 4. Tap "Start Face Registration"                  │
└────────────┬────────────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────────────┐
│          CAMERA CAPTURE (Device Camera)             │
│                                                     │
│ • Open camera                                      │
│ • Show instruction: "Hadap ke kamera"             │
│ • Pose 1: Depan (0°)                              │
│ • Pose 2: Kiri (45°)                              │
│ • Pose 3: Kanan (45°)                             │
│ • Pose 4: Atas                                    │
│ • Pose 5: Bawah                                   │
│ • ... (repeat untuk 10+ poses)                    │
│                                                     │
│ For each capture:                                  │
│ • Take screenshot (base64)                         │
│ • Send to JavaScript processing                    │
└────────────┬────────────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────────────┐
│   FACE PROCESSING (JavaScript/TensorFlow.js)       │
│   (Runs locally in React Native app)                │
│                                                     │
│ For each photo:                                    │
│ ├─ Step 1: Detect face in image                   │
│ │           (using TensorFlow face detection)      │
│ ├─ Step 2: Extract 128-dim descriptor             │
│ │           (face embedding/vector)                │
│ ├─ Step 3: Assess quality                         │
│ │           ├─ Brightness check                    │
│ │           ├─ Blur detection                      │
│ │           ├─ Multiple faces check                │
│ │           ├─ Face size check                     │
│ │           └─ Confidence score                    │
│ ├─ Step 4: Accept/Reject based on quality        │
│ │           (if quality > threshold: keep it)     │
│ ├─ Step 5: Add to samples array                   │
│ │           samples = [descriptor_1, desc_2, ...]│
│ └─ Step 6: Show feedback                         │
│            "Sample 1/10 collected" ✓              │
│                                                     │
│ Repeat until 10+ quality samples collected        │
└────────────┬────────────────────────────────────────┘
             │
             ↓
     [Auto-trigger Upload]
             │
             ↓
┌─────────────────────────────────────────────────────┐
│      UPLOAD TO LARAVEL (HTTP POST)                  │
│                                                     │
│ POST /api/v1/mobile/pic/users/{userId}/face       │
│                                                     │
│ Body: {                                            │
│   "descriptors": [                                 │
│     [0.1, -0.2, 0.15, ..., 0.08],    // 128 floats│
│     [0.12, -0.19, ..., 0.09],         // Sample 2 │
│     [0.11, -0.21, ..., 0.07],         // Sample 3 │
│     ...                                            │
│     [0.13, -0.17, ..., 0.10]          // Sample 10│
│   ]                                                │
│ }                                                  │
│                                                     │
│ • Validate 10+ descriptors × 128 floats each     │
│ • Check user authorization                        │
│ • Generate response                               │
└────────────┬────────────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────────────┐
│   LARAVEL DATABASE STORAGE (jez_sistem)             │
│                                                     │
│ • Parse existing u_face JSON                       │
│ • Add new samples to array                         │
│ • Create face data structure:                      │
│                                                     │
│ $faceData = {                                      │
│   "mode": "registration",                          │
│   "registered_at": "2024-04-03T14:30:00Z",       │
│   "samples": [                                     │
│     {                                              │
│       "id": "sample_1712084100_4521",            │
│       "descriptor": [0.1, -0.2, ..., 0.08],     │
│       "timestamp": "2024-04-03T14:30:00Z"       │
│     },                                            │
│     ... (9 more samples)                          │
│   ]                                                │
│ }                                                  │
│                                                     │
│ • Encode as JSON                                   │
│ • Execute: UPDATE users SET u_face = '{...}'      │
│ • Return success response                         │
└────────────┬────────────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────────────┐
│      MYSQL DATABASE (jez_erp)                       │
│                                                     │
│ Table: users                                       │
│ Column: u_face (LONGTEXT)                          │
│                                                     │
│ Row for user_id=1:                                 │
│ ┌─────────────────────────────────────┐           │
│ │ id: 1                               │           │
│ │ u_name: "Budi Santoso"              │           │
│ │ u_email: "budi@company.com"         │           │
│ │ u_face: {                           │           │
│ │   "mode": "registration",           │           │
│ │   "registered_at": "2024-04-03..."  , │           │
│ │   "samples": [                      │           │
│ │     {descriptor: [...]},            │           │
│ │     ... (10 samples)                │           │
│ │   ]                                 │           │
│ │ }                                   │           │
│ └─────────────────────────────────────┘           │
│                                                     │
│ ✓ REGISTRASI SELESAI!                             │
│ ✓ Ready untuk daily attendance                    │
└─────────────────────────────────────────────────────┘
```

---

### Fase 2: DAILY ATTENDANCE (Penggunaan Harian)

```
┌─────────────────────────────────────────────────────┐
│      REACT NATIVE APP (Employee)                    │
│                                                     │
│ 1. Employee open app                              │
│ 2. Login with username/password                    │
│ 3. Select "Scan Face for Attendance"             │
│ 4. Tap camera button                              │
└────────────┬────────────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────────────┐
│      SINGLE FACE CAPTURE                            │
│                                                     │
│ • Open camera                                      │
│ • Employee face to camera                          │
│ • Take 1 photo (automatic or manual button)       │
│ • Convert to base64                                │
└────────────┬────────────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────────────┐
│   EXTRACT FACE DESCRIPTOR (JavaScript)              │
│                                                     │
│ • Detect face in photo                             │
│ • Extract 128-dimensional vector                   │
│ • Result: [0.12, -0.19, 0.14, ..., 0.09]        │
│          (1 array × 128 floats)                   │
└────────────┬────────────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────────────┐
│    SEND TO LARAVEL FOR IDENTIFICATION               │
│                                                     │
│ POST /api/v1/mobile/public/attendance/identify     │
│                                                     │
│ Body: {                                            │
│   "face_descriptor": [0.12, -0.19, 0.14, ...]    │
│ }                                                  │
│                                                     │
│ • No token needed (public endpoint)                │
│ • Only send 1 descriptor (the live one)           │
└────────────┬────────────────────────────────────────┘
             │
             ↓
┌─────────────────────────────────────────────────────┐
│   LARAVEL IDENTIFICATION LOGIC                      │
│                                                     │
│ GET all active users with faces registered        │
│ For each user:                                     │
│   GET their 10 stored descriptors from u_face     │
│   CALCULATE distance between:                     │
│     - Live descriptor (1 sample)                   │
│     - Each of 10 stored descriptors               │
│   FIND best match (lowest distance)                │
│   CALCULATE confidence score                       │
│                                                     │
│ Result: {                                          │
│   "matched": true/false,                          │
│   "user_id": 1,                                    │
│   "distance": 0.25,                                │
│   "confidence": 0.95                               │
│ }                                                  │
│                                                     │
│ Threshold: If distance < 0.4 → Matched ✓         │
│            If distance > 0.4 → Not matched ✗      │
└────────────┬────────────────────────────────────────┘
             │
             ↓
    [Check if Matched]
      /            \
   YES              NO
    │               │
    ↓               ↓
┌──────────┐  ┌──────────────┐
│ MATCHED! │  │ NOT MATCHED! │
│          │  │              │
│Record    │  │Show error    │
│attendance│  │message       │
└──────────┘  │"Try again"   │
              └──────────────┘
```

---

## 🔑 Key Concepts

### Apa itu Descriptor?

**Descriptor** = Representasi numerikal dari wajah seseorang

```
Real Face             → Processing              → Descriptor
[Image pixels]        → TensorFlow/dlib         → [128 floats]

Example:
Face of "Budi"        → Extract                 → [0.12, -0.19, 0.14, 
                                                   0.05, -0.23, 0.08, 
                                                   ... (128 numbers)]
```

- **Ukuran**: Selalu 128 floating-point numbers
- **Invariant**: Same person = similar descriptors (even with diff angles/lighting)
- **Unique**: Different people = different descriptors

### Matching Process

```
Live Descriptor (from employee's photo):
  [0.12, -0.19, 0.14, 0.05, -0.23, ...]

Stored Descriptor #1 (from registration sample 1):
  [0.11, -0.20, 0.13, 0.04, -0.22, ...]
  
Distance = √[(0.12-0.11)² + (-0.19-(-0.20))² + ...] = 0.15

Stored Descriptor #2:
  [0.14, -0.18, 0.15, 0.06, -0.24, ...]
  Distance = √[(0.12-0.14)² + ...] = 0.22

Stored Descriptor #3:
  [0.08, -0.25, 0.10, 0.02, -0.20, ...]
  Distance = √[...] = 0.45

... (check all 10)

Best Match: Descriptor #1 with distance = 0.15 ✓
Threshold: 0.4
Result: 0.15 < 0.4 → MATCHED!
```

### Mengapa 10+ Samples?

```
Dengan hanya 1 sample saat registrasi:
  Registration:   Employee pose depan     → Save 1 descriptor
  Daily:          Employee pose kiri      → Extract 1 descriptor
  Matching:       Depan ≠ Kiri             → Distance besar → NO MATCH ✗

Dengan 10+ samples dari berbagai sudut:
  Registration:   
    Sample 1: Depan    → Save descriptor_1
    Sample 2: Kiri     → Save descriptor_2
    Sample 3: Kanan    → Save descriptor_3
    Sample 4: Atas     → Save descriptor_4
    Sample 5: Bawah    → Save descriptor_5
    ... (berbagai pose/lighting)
    
  Daily:          
    Employee pose: Kiri
    Extracted: descriptor_live
    
  Matching:
    Compare to descriptor_2 (kiri)    → Distance 0.15 ✓ MATCH!
    Compare to descriptor_1 (depan)   → Distance 0.22 (OK)
    Compare to descriptor_3 (kanan)   → Distance 0.19 (OK)
    ... (semua match)
    
Result: Confidence 0.95 → MATCHED! ✓
```

---

## 📋 Step-by-Step Workflow

### Registration Workflow (PIC Admin)

| Step | Action | Details |
|------|--------|---------|
| 1 | Open React Native App | App di device |
| 2 | Login as PIC | Email: admin@test.com |
| 3 | Select Menu | "Register User Faces" |
| 4 | Search Employee | Find "Budi Santoso" |
| 5 | Click to Register | Select user |
| 6 | Open Camera | "Start Face Registration" |
| 7 | First Capture | Pose: Depan (straight) |
| 8 | Process | Detect face → Extract descriptor |
| 9 | Quality Check | Score: 0.95 ✓ OK |
| 10 | Save Sample | Sample 1/10 |
| 11 | Repeat Captures | Captures 2-10 dari sudut berbeda |
| 12 | Auto Upload | Setelah 10 sampel: Auto POST ke Laravel |
| 13 | Database Save | Laravel simpan ke jez_erp.users.u_face |
| 14 | Success | "Registration complete!" |
| 15 | Verify DB | Query u_face column: 10 descriptors saved |

### Attendance Workflow (Employee)

| Step | Action | Details |
|------|--------|---------|
| 1 | Open React Native App | App di device |
| 2 | Login | Email/Password karyawan |
| 3 | Select Attendance | "Scan Face" button |
| 4 | Open Camera | Camera nyala |
| 5 | Face to Camera | "Hadap ke camera" |
| 6 | Capture | Take 1 photo |
| 7 | Extract | Process descriptor locally |
| 8 | Send | POST to identify endpoint |
| 9 | Match | Laravel cocok dengan 10 stored |
| 10 | Result | If match → "Selamat pagi Budi!" |
| 11 | Record | Save attendance record |
| 12 | Done | ✓ Attendance recorded |

---

## 🛠️ Technical Details

### Database Schema

```sql
-- Table: users
-- Database: jez_erp

CREATE TABLE users (
    id INT PRIMARY KEY,
    u_name VARCHAR(255),
    u_email VARCHAR(255),
    u_phone VARCHAR(20),
    u_nip VARCHAR(50),
    u_face LONGTEXT COMMENT 'JSON containing face descriptors'
    -- ... other columns
);

-- Example content of u_face column:
{
  "mode": "registration",
  "registered_at": "2024-04-03T14:30:00Z",
  "samples": [
    {
      "id": "sample_1712084100_4521",
      "descriptor": [
        0.1234, -0.2341, 0.1567, -0.0898, 0.0456, 
        0.1678, -0.0789, 0.2345, 0.0891, -0.1456,
        ... (128 numbers total)
      ],
      "timestamp": "2024-04-03T14:30:00Z"
    },
    ... (9 more samples)
  ]
}
```

### API Endpoints

**Registration:**
```
POST /api/v1/mobile/pic/users/{userId}/face
Headers: Authorization: Bearer {token}
Body: {
  "descriptors": [[...128], [...128], ..., [...128]]  // 10+ arrays
}
```

**Identification:**
```
POST /api/v1/mobile/public/attendance/identify
Body: {
  "face_descriptor": [...128]  // 1 array
}
Response: {
  "matched": true/false,
  "user": {...},
  "confidence": 0.95
}
```

---

## 💾 Data Storage

### During Registration

```python
# App (JavaScript)
samples = [
    {"descriptor": [0.1, -0.2, ...128 floats]},
    {"descriptor": [0.12, -0.19, ...128 floats]},
    ... (10 samples)
]

# Send to Laravel
POST /api/v1/mobile/pic/users/1/face
{
  "descriptors": [[0.1, -0.2, ...], [0.12, -0.19, ...], ...]
}
```

### In Database

```json
{
  "mode": "registration",
  "registered_at": "2024-04-03T14:30:00Z",
  "samples": [
    {"id": "s1", "descriptor": [0.1, -0.2, ...], "timestamp": "..."},
    {"id": "s2", "descriptor": [0.12, -0.19, ...], "timestamp": "..."},
    ...
    {"id": "s10", "descriptor": [...], "timestamp": "..."}
  ]
}
```

### During Daily Attendance

```python
# App extracts 1 descriptor
live_descriptor = [0.11, -0.21, ...128 floats]

# Send to Laravel
POST /api/v1/mobile/public/attendance/identify
{
  "face_descriptor": [0.11, -0.21, ...]
}

# Laravel matches against stored 10 descriptors
# Returns: matched user or "not found"
```

---

## ✅ Verification Checklist

### Pre-Implementation
- [ ] Database jez_erp exists
- [ ] Table users exists
- [ ] Column u_face exists (LONGTEXT type)
- [ ] Laravel API running
- [ ] React Native app installed

### After Registration
- [ ] Query database: `SELECT JSON_LENGTH(u_face, '$.samples') FROM users WHERE id=1;`
- [ ] Expected output: `10` (or more)
- [ ] Check timestamp: `SELECT JSON_EXTRACT(u_face, '$.registered_at') FROM users WHERE id=1;`

### Daily Usage
- [ ] Employee can login
- [ ] Camera opens successfully
- [ ] Photo captured and processed
- [ ] Identify endpoint returns match result
- [ ] Attendance recorded in database

---

## 🚀 Kesimpulan

Sistem pendaftaran wajah bekerja dengan:

1. **Registration Phase**: Sekali saja per karyawan
   - Ambil 10+ foto dari berbagai sudut
   - Extract descriptor dari setiap foto
   - Upload ke database
   - Simpan di users.u_face JSON

2. **Daily Phase**: Setiap hari saat absen
   - Ambil 1 foto wajah
   - Extract descriptor
   - Cocok dengan 10 stored descriptors
   - Jika match → Record attendance

3. **Data Storage**: JSON di database column
   - 10 descriptors × 128 floats = 1280 numbers per user
   - Compact dan efficient
   - Mudah untuk backup

**Sistem siap production!** ✨

---

## 📖 Dokumentasi Terkait

- `REGISTRATION_WORKFLOW.md` - Detailed workflow explanation
- `IMPLEMENTATION_GUIDE.md` - Step-by-step implementation
- `DATABASE_CONFIG.md` - Database configuration details
- `INTEGRATION_GUIDE.md` - Complete integration architecture
- `README.md` - API endpoint reference

Baca semua file dokumentasi untuk pemahaman lengkap! 📚
