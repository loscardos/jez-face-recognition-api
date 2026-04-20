# Panduan Implementasi Praktis - Face Registration System

## Pre-requisites

### Sebelum Mulai, Pastikan:

- ✅ Database: `jez_erp` sudah ada
- ✅ Table: `users` sudah ada  
- ✅ Column: `u_face` sudah ada (LONGTEXT type)
- ✅ Laravel Backend: Jalan di `http://localhost:8000` (atau URL produksi)
- ✅ React Native App: Sudah ter-setup dengan Vision Camera
- ✅ Python Backend: Optional (hanya untuk advanced processing)

### Check Database Column

```bash
# Connect to MySQL
mysql -h db -u root -p jez_erp

# Check column exists
SHOW COLUMNS FROM users LIKE 'u_face';

# Expected output:
# Field   | Type           | Null | Key | Default | Extra
# u_face  | longtext       | YES  |     | NULL    |

# Jika tidak ada, create:
ALTER TABLE users 
ADD COLUMN u_face LONGTEXT COMMENT 'Face recognition data (JSON)';
```

---

## Step 1: Setup Laravel Backend

### Pastikan API Endpoint Siap

Cek file: `/home/royyan/projects/jez_sistem/routes/api.php`

Harus ada route:
```php
Route::middleware('auth:sanctum')->group(function () {
    Route::prefix('v1/mobile')->group(function () {
        // ... existing routes ...
        Route::get('/pic/users', [MobileAttendanceController::class, 'picUsers']);
        Route::get('/pic/users/{user}/face', [MobileAttendanceController::class, 'picUserFace']);
        Route::post('/pic/users/{user}/face', [MobileAttendanceController::class, 'picStoreFace']);
        Route::post('/attendance/submit', [MobileAttendanceController::class, 'submit']);
    });
});

Route::prefix('v1/mobile/public')->group(function () {
    Route::post('/attendance/identify', [MobileAttendanceController::class, 'identify']);
});
```

### Update MobileAttendanceController

Pastikan method `picStoreFace` ada dan menghandle descriptors:

```php
public function picStoreFace(Request $request, User $user)
{
    $actor = $request->user();
    
    // Validate
    $validated = $request->validate([
        'descriptors' => 'nullable|array|min:1',
        'descriptors.*' => 'array|size:128',
        'descriptors.*.*' => 'numeric',
        'photos' => 'nullable|array'
    ]);
    
    // Parse existing face data
    $faceData = json_decode($user->u_face ?? 'null', true) ?? [];
    
    // Add descriptors if provided
    if (!empty($validated['descriptors'])) {
        $samples = $faceData['samples'] ?? [];
        
        foreach ($validated['descriptors'] as $descriptor) {
            $samples[] = [
                'id' => 'sample_' . time() . '_' . rand(1000, 9999),
                'descriptor' => $descriptor,
                'timestamp' => now()->toIso8601String()
            ];
        }
        
        // Update face data
        $faceData = [
            'mode' => 'registration',
            'registered_at' => $faceData['registered_at'] ?? now()->toIso8601String(),
            'samples' => $samples
        ];
        
        // Save to database
        $user->update([
            'u_face' => json_encode($faceData)
        ]);
    }
    
    return response()->json([
        'status' => 'success',
        'message' => 'Wajah berhasil disimpan',
        'data' => [
            'user' => $this->formatUserSummary($user->fresh()),
            'descriptor_count' => count($faceData['samples'] ?? [])
        ]
    ]);
}
```

### Test Laravel API

```bash
# 1. Get authentication token
curl -X POST http://localhost:8000/api/login \
  -H "Content-Type: application/json" \
  -d '{"u_email":"admin@test.com", "password":"password"}'

# Response: {"status":"200", "token":"abc123...", "user":{...}}

TOKEN="abc123..."

# 2. Get user list
curl -X GET "http://localhost:8000/api/v1/mobile/pic/users?search=" \
  -H "Authorization: Bearer $TOKEN"

# 3. Submit descriptors for user ID 1
curl -X POST http://localhost:8000/api/v1/mobile/pic/users/1/face \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "descriptors": [
      [0.1, -0.2, 0.15, ...(128 floats)...],
      [0.12, -0.19, ...(128 floats)...],
      ... (up to 10+ arrays)
    ]
  }'

# Response: {"status":"success", "message":"...", "data":{...}}
```

---

## Step 2: Verify React Native App

### API Configuration

File: `/home/royyan/projects/face-id/src/services/mobileApi.ts`

Pastikan API_BASE_URL benar:

```typescript
// For development (local network)
const API_BASE_URL = "http://192.168.1.100:8000/api";  // Your machine IP

// For production
const API_BASE_URL = "https://api.yourcompany.com/api";
```

### Required Methods Ada

Cek mobileApi service punya methods ini:

```typescript
// Login
login(u_email: string, password: string): Promise<LoginResponse>

// Get PIC users list
getPicUsers(token: string, search: string): Promise<PicUser[]>

// Get user face detail
getPicUserFaceDetail(token: string, userId: number): Promise<PicFaceDetail>

// Store face descriptors
storePicUserFace(token: string, userId: number, payload): Promise<PicFaceDetail>

// Identify face for attendance
identifyPublicFace(face_descriptor: number[]): Promise<AttendanceScanResult>
```

### Test React Native App

```bash
# 1. Build and run
cd /home/royyan/projects/face-id
npm install
npm run android  # atau npm run ios

# 2. Login sebagai PIC dengan credentials: admin@test.com / password

# 3. Test flow:
#    - Buka Users list
#    - Klik satu user
#    - Click "Register Face"
#    - Kamera akan nyala
#    - Take test screenshots
#    - Verify descriptors extracted
#    - Click submit
#    - Verify success message
```

---

## Step 3: Test Registrasi Flow

### Test Scenario 1: Manual Descriptor Upload

```bash
# Generate dummy descriptors (for testing, without real face)
python3 << 'EOF'
import json
import random

# Create 10 sample descriptors (128 floats each)
descriptors = []
for i in range(10):
    descriptor = [random.uniform(-1, 1) for _ in range(128)]
    descriptors.append(descriptor)

print(json.dumps(descriptors, indent=2))
EOF

# Save to file
python3 -c "
import json, random
descriptors = [[random.uniform(-1, 1) for _ in range(128)] for _ in range(10)]
with open('/tmp/descriptors.json', 'w') as f:
    json.dump(descriptors, f)
" && cat /tmp/descriptors.json

# Submit to Laravel
TOKEN="your_token_here"
curl -X POST http://localhost:8000/api/v1/mobile/pic/users/1/face \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d @/tmp/descriptors.json

# Actually send as payload
curl -X POST http://localhost:8000/api/v1/mobile/pic/users/1/face \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "descriptors": [
      [0.123, -0.234, 0.156, -0.089, 0.045, 0.167, -0.078, 0.234, 0.089, -0.145, 0.256, 0.034, -0.167, 0.123, 0.089, -0.234, 0.156, 0.012, -0.145, 0.234, 0.123, -0.089, 0.156, 0.234, -0.078, 0.145, 0.089, 0.234, -0.156, 0.123, 0.089, -0.234, 0.156, 0.012, -0.145, 0.234, 0.123, -0.089, 0.156, 0.234, -0.078, 0.145, 0.089, 0.234, -0.156, 0.123, 0.089, -0.234, 0.156, 0.012, -0.145, 0.234, 0.123, -0.089, 0.156, 0.234, -0.078, 0.145, 0.089, 0.234, -0.156, 0.123, 0.089, -0.234, 0.156, 0.012, -0.145, 0.234, 0.123, -0.089, 0.156, 0.234, -0.078, 0.145, 0.089, 0.234, -0.156, 0.123, 0.089, -0.234, 0.156, 0.012, -0.145, 0.234, 0.123, -0.089, 0.156, 0.234, -0.078, 0.145, 0.089, 0.234, -0.156, 0.123, 0.089, -0.234, 0.156, 0.012, -0.145, 0.234, 0.123, -0.089, 0.156, 0.234, -0.078, 0.145, 0.089, 0.234, -0.156, 0.123, 0.089, -0.234, 0.156, 0.012, -0.145, 0.234, 0.123, -0.089, 0.156, 0.234, -0.078, 0.145]
    ]
  }'
```

### Test Scenario 2: Verify Database

```sql
-- Check data tersimpan
SELECT 
    id,
    u_name,
    JSON_EXTRACT(u_face, '$.mode') as mode,
    JSON_EXTRACT(u_face, '$.registered_at') as registered_at,
    JSON_LENGTH(u_face, '$.samples') as descriptor_count
FROM users
WHERE u_face IS NOT NULL
LIMIT 5;

-- Lihat detail 1 user
SELECT 
    id,
    u_name,
    u_face
FROM users
WHERE id = 1;

-- Count users dengan face registered
SELECT COUNT(*) as registered_count
FROM users
WHERE u_face IS NOT NULL;
```

---

## Step 4: Initialize All Users (Batch Registration)

Jika perlu registrasi untuk banyak karyawan:

### Option 1: Via React Native App (Manual)
- PIC login ke app
- Daftar satu-satu per karyawan
- Ambil 10+ foto per orang
- ±5-10 menit per orang

### Option 2: Batch Reset (Testing)
```sql
-- Clear all face data (untuk testing ulang)
UPDATE users SET u_face = NULL;

-- Verify cleared
SELECT COUNT(*) as cleared FROM users WHERE u_face IS NULL;
```

### Option 3: Seed via Script (Development)

```python
# Script untuk testing: seed_faces.py
import requests
import json
import random

API_URL = "http://localhost:8000/api"
TOKEN = "your_token"

# Create fake descriptors (for testing without real camera)
def create_fake_descriptor():
    return [random.uniform(-1, 1) for _ in range(128)]

# Register 5 test users with dummy data
for user_id in range(1, 6):
    descriptors = [create_fake_descriptor() for _ in range(10)]
    
    payload = {
        "descriptors": descriptors
    }
    
    response = requests.post(
        f"{API_URL}/v1/mobile/pic/users/{user_id}/face",
        json=payload,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json"
        }
    )
    
    print(f"User {user_id}: {response.json()}")

# Verify
response = requests.get(
    f"{API_URL}/v1/admin/users",
    headers={"Authorization": f"Bearer {TOKEN}"}
)
print(f"\nTotal users: {len(response.json()['data'])}")
```

---

## Step 5: Test Daily Attendance

Setelah registrasi selesai, test penggunaan:

### Flow Test

```bash
# 1. Generate 1 descriptor (simulasi live capture)
python3 << 'PYEOF'
import json, random
descriptor = [random.uniform(-1, 1) for _ in range(128)]
print(json.dumps(descriptor))
PYEOF

# 2. Save to file
python3 -c "
import json, random
with open('/tmp/live_descriptor.json', 'w') as f:
    json.dump([random.uniform(-1, 1) for _ in range(128)], f)
" && cat /tmp/live_descriptor.json

# 3. Test identify endpoint
DESCRIPTOR=$(cat /tmp/live_descriptor.json | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin)))")

curl -X POST http://localhost:8000/api/v1/mobile/public/attendance/identify \
  -H "Content-Type: application/json" \
  -d "{\"face_descriptor\": $DESCRIPTOR}"

# Expected response:
# {
#   "status": "success",
#   "data": {
#     "user": {"id": 1, "u_name": "...", "u_nip": "..."},
#     "match": {"matched": true, "confidence": 0.85, ...}
#   }
# }
```

---

## Checklist Implementasi

### Pre-Implementation
- [ ] Database `jez_erp` sudah ada
- [ ] Table `users` sudah ada
- [ ] Column `u_face` sudah ada (LONGTEXT)
- [ ] Laravel backend running
- [ ] React Native environment setup

### Implementation
- [ ] Laravel API endpoints tested
- [ ] React Native app API calls working
- [ ] Face detection working (JavaScript TensorFlow)
- [ ] Descriptor extraction working
- [ ] Quality assessment implemented
- [ ] Database storage working

### Testing
- [ ] Test registrasi 1 user via app
- [ ] Verify data di database `jez_erp`
- [ ] Test identify endpoint
- [ ] Test attendance submission
- [ ] Test dengan multiple users

### Deployment
- [ ] Setup HTTPS/SSL
- [ ] Configure CORS untuk production
- [ ] Database backup procedure
- [ ] Monitoring & logging setup
- [ ] User training

---

## Troubleshooting Common Issues

### Issue: "Column u_face not found"
```sql
ALTER TABLE users ADD COLUMN u_face LONGTEXT;
```

### Issue: "API 404 not found"
- Verify Laravel API URL in React Native app
- Check routes defined in api.php
- Verify Sanctum middleware configured

### Issue: "Descriptor mismatch error"
- Check descriptor array size: must be 128 floats
- Verify JSON encoding correct
- Test dengan curl first sebelum mobile app

### Issue: "Face tidak terdeteksi di camera"
- Check Vision Camera permission
- Improve lighting
- Ensure proper face pose/distance

### Issue: "Low match confidence"
- Add more samples during registration (10+)
- Vary angles and lighting during registration
- Check face quality during registration

---

## Performance Optimization

### Untuk Produksi

1. **Database Optimization**
```sql
-- Add index untuk faster queries
ALTER TABLE users ADD INDEX idx_u_face (u_face(100));
```

2. **Caching** (di Laravel)
```php
// Cache face data untuk faster identification
$faceData = Cache::remember('face_data:all', 300, function() {
    return User::whereNotNull('u_face')
        ->select('id', 'u_face')
        ->get();
});
```

3. **Batch Processing** (di Python)
- Pre-load semua descriptors on startup
- Cache identification results
- Use CPU-fast computation

4. **Image Compression**
- Compress face images sebelum upload
- Reduce network bandwidth
- Faster processing

---

## Summary

**Implementasi 5 Steps:**
1. ✅ Setup Laravel Backend
2. ✅ Verify React Native App  
3. ✅ Test Registrasi Flow
4. ✅ Initialize All Users
5. ✅ Test Daily Attendance

**Key Points:**
- Database: jez_erp.users.u_face
- Registrasi: 10+ descriptors per user
- Attendance: 1 descriptor match ke 10 stored
- Workflow: Complete dari mobile → Laravel → DB

**Siap Produksi!** 🚀
