# Workflow Pendaftaran Wajah (Face Registration)

## Konsep Umum

Sistem face recognition memerlukan 2 fase:

### Fase 1: REGISTRASI (Registration) - Dilakukan Sekali
- Admin/PIC mengambil 10+ foto wajah karyawan
- Setiap foto diproses untuk ekstrak descriptor (128 floats)
- Descriptors disimpan ke database jez_erp, users.u_face (JSON column)

### Fase 2: PENGGUNAAN HARIAN (Daily Usage)
- Karyawan scan wajah mereka 1x saat absen
- Sistem cocokkan dengan 10+ descriptors yang sudah disimpan
- Jika match → Attendance recorded ✓

---

## Detail Flow Registrasi

### 1. PIC Login ke Mobile App

```javascript
// React Native App
const login = async (email, password) => {
  const response = await fetch('/api/login', {
    method: 'POST',
    body: JSON.stringify({ u_email: email, password })
  });
  
  const { token, user } = await response.json();
  // User adalah PIC (admin yang mendaftarkan wajah)
  return { token, user };
};
```

### 2. PIC Pilih Karyawan untuk Didaftarkan

```javascript
// Get list karyawan
const getPicUsers = async (token) => {
  const response = await fetch('/api/v1/mobile/pic/users', {
    headers: { Authorization: `Bearer ${token}` }
  });
  
  return response.json(); // List of users
};

// Klik satu user untuk mulai registrasi
const selectEmployee = (user) => {
  // Open camera untuk registrasi wajah user ini
  openCamera('registration', user.id);
};
```

### 3. Capture & Process Wajah

Untuk setiap capture:

```javascript
// Quando camera take photo
const onCameraCapture = async (photoBase64) => {
  // Step 1: Detect wajah di gambar
  const faces = await faceDetector.detect(image);
  
  if (faces.length === 0) {
    alert('Wajah tidak terdeteksi, coba lagi');
    return;
  }
  
  if (faces.length > 1) {
    alert('Multiple faces detected, hanya 1 wajah saja');
    return;
  }
  
  // Step 2: Extract descriptor (128 floats)
  const face = faces[0];
  const descriptor = extractFaceDescriptor(image, face);
  
  // Step 3: Quality assessment
  const quality = assessQuality({
    lighting: face.brightness,
    pose: face.angle,
    size: (face.width * face.height) / (image.width * image.height),
    blur: detectBlur(image)
  });
  
  if (quality.score < 0.5) {
    alert(`Kualitas wajah kurang bagus: ${quality.feedback}`);
    return;
  }
  
  // Step 4: Simpan descriptor
  addSample({
    id: `sample_${samplesCount}`,
    descriptor: descriptor, // [0.1, -0.2, 0.15, ...]
    timestamp: new Date(),
    qualityScore: quality.score
  });
  
  showFeedback(`Sample ${samplesCount}/10 tersimpan`);
};
```

### 4. Collect 10+ Samples

Sistem menunggu sampai ada 10 samples dengan kualitas bagus:

```javascript
const samples = [
  { id: 's1', descriptor: [...], qualityScore: 0.95 }, // Depan
  { id: 's2', descriptor: [...], qualityScore: 0.92 }, // Kiri 45°
  { id: 's3', descriptor: [...], qualityScore: 0.93 }, // Kanan 45°
  { id: 's4', descriptor: [...], qualityScore: 0.91 }, // Atas
  { id: 's5', descriptor: [...], qualityScore: 0.94 }, // Bawah
  { id: 's6', descriptor: [...], qualityScore: 0.89 }, // Tersenyum
  { id: 's7', descriptor: [...], qualityScore: 0.90 }, // Serius
  { id: 's8', descriptor: [...], qualityScore: 0.88 }, // Cahaya berbeda
  { id: 's9', descriptor: [...], qualityScore: 0.91 }, // Jarak berbeda
  { id: 's10', descriptor: [...], qualityScore: 0.93 }  // Angle berbeda
];

// Ketika 10 samples terkumpul, auto-submit
if (samples.length >= 10) {
  submitRegistration(samples);
}
```

### 5. Upload ke Laravel

```javascript
const submitRegistration = async (samples) => {
  const descriptors = samples.map(s => s.descriptor);
  
  const response = await fetch(
    `/api/v1/mobile/pic/users/${userId}/face`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        descriptors: descriptors // 10 arrays, each with 128 floats
      })
    }
  );
  
  if (response.ok) {
    alert('Registrasi berhasil! Wajah tersimpan di database.');
  }
};
```

### 6. Laravel Simpan ke Database

```php
// app/Http/Controllers/Api/MobileAttendanceController.php

public function storePicUserFace(Request $request, User $user)
{
    // Input validation
    $validated = $request->validate([
        'descriptors' => 'required|array|min:10',
        'descriptors.*' => 'array|size:128',
        'descriptors.*.*' => 'numeric'
    ]);
    
    // Parse existing face data
    $faceData = json_decode($user->u_face, true) ?? [];
    
    // Add new samples
    $samples = [];
    foreach ($validated['descriptors'] as $descriptor) {
        $samples[] = [
            'id' => 'sample_' . time() . '_' . rand(1000, 9999),
            'descriptor' => $descriptor,
            'timestamp' => now()->toIso8601String()
        ];
    }
    
    // Update u_face JSON
    $faceData = [
        'mode' => 'registration',
        'registered_at' => now()->toIso8601String(),
        'samples' => $samples
    ];
    
    // Save to database
    $user->update(['u_face' => json_encode($faceData)]);
    
    return response()->json([
        'status' => 'success',
        'message' => 'Wajah berhasil didaftarkan',
        'data' => [
            'user_id' => $user->id,
            'descriptor_count' => count($samples),
            'registered_at' => $faceData['registered_at']
        ]
    ]);
}
```

### 7. Database Storage (jez_erp)

```sql
-- Table structure
CREATE TABLE users (
    id INT PRIMARY KEY,
    u_name VARCHAR(255),
    u_email VARCHAR(255),
    ...
    u_face LONGTEXT COMMENT 'JSON with face descriptors',
    ...
);

-- Data struktur u_face:
{
  "mode": "registration",
  "registered_at": "2024-04-03T14:30:00Z",
  "samples": [
    {
      "id": "sample_1712084100_4521",
      "descriptor": [
        0.124, -0.234, 0.156, -0.089, 0.045, ... (128 floats total)
      ],
      "timestamp": "2024-04-03T14:30:00Z"
    },
    {
      "id": "sample_1712084105_7834",
      "descriptor": [
        0.121, -0.231, 0.152, -0.087, 0.043, ... (128 floats total)
      ],
      "timestamp": "2024-04-03T14:30:05Z"
    },
    ... (more samples up to 10+)
  ]
}
```

---

## Daily Usage - Absen dengan Wajah

Setelah registrasi selesai, karyawan bisa absen:

### Workflow

```
1. Karyawan buka app
2. Login dengan username/password
3. Tap "Scan Face untuk Absen"
4. Kamera nyala
5. Ambil 1 foto wajah
6. App extract descriptor (1 array x 128 floats)
7. Kirim ke Laravel: POST /api/attendance/identify
8. Laravel cari match di database:
   ├─ Ambil all users' descriptors
   ├─ Hitung jarak ke descriptor live
   ├─ Cari yang paling dekat
   └─ Return matched user jika confidence > threshold
9. Jika match → Record attendance + Photo stored
   Jika tidak match → "Wajah tidak dikenali, coba lagi"
```

### Code Example

```javascript
// Upload descriptors untuk matching
const identifyFace = async (liveDescriptor) => {
  const response = await fetch(
    '/api/v1/mobile/public/attendance/identify',
    {
      method: 'POST',
      body: JSON.stringify({
        face_descriptor: liveDescriptor // 1 array x 128 floats
      })
    }
  );
  
  const result = await response.json();
  
  if (result.status === 'success') {
    const { user, match } = result.data;
    if (match.matched) {
      // User identified!
      alert(`Selamat pagi ${user.u_name}!`);
      recordAttendance(user.id);
    }
  } else {
    alert('Wajah tidak dikenal');
  }
};
```

---

## Perbandingan: Registration vs Daily Usage

| Aspek | Registration | Daily Usage |
|-------|--------------|-------------|
| **Frekuensi** | Sekali per karyawan | Setiap hari |
| **Jumlah Sampel** | 10+ foto | 1 foto |
| **Descriptors** | 10 arrays × 128 floats | 1 array × 128 floats |
| **Waktu** | ±5 menit per orang | ±30 detik per orang |
| **Tujuan** | Collect reference data | Matching live face |
| **Storage** | Disimpan di users.u_face | Tidak disimpan |
| **Operator** | PIC/Admin | Setiap karyawan sendiri |

---

## Mengapa 10+ Samples?

### Skenario Berbeda saat Absen Harian

Ketika karyawan scan wajah di attendance, mereka mungkin:
- Datang dari arah berbeda (sudut berbeda)
- Waktu berbeda (lighting berbeda)
- Keadaan berbeda (cape, sakit, tersenyum, serius)
- Environment berbeda (outdoor, indoor)

Dengan 10 samples dari berbagai sudut/kondisi saat registrasi:
- ✓ Descriptor akan match meskipun kondisinya berbeda
- ✓ Akurasi lebih tinggi (tidak false positive)
- ✓ Robustness lebih baik (tidak sensetif perubahan minor)

Jika hanya 1 sample saat registrasi:
- ✗ Hanya cocok jika scan dari sudut sama
- ✗ Jika cahaya berbeda, bisa tidak cocok
- ✗ Ekspresi wajah sedikit berbeda = tidak cocok
- ✗ Mudah false negative

### Analogi

Seperti paspor:
- Registration = Foto resmi di banyak kondisi + berbagai sudut
- Daily usage = Foto wajah "jelek" saat sibuk, tapi tetap dikenali

---

## Testing Registrasi

### Langkah-langkah Test

```bash
# 1. Pastikan Laravel & Python backend running
# 2. Login ke React Native app sebagai PIC

# 3. Test dengan dummy data
curl -X POST http://localhost:8000/api/v1/mobile/pic/users/1/face \
  -H "Authorization: Bearer token" \
  -H "Content-Type: application/json" \
  -d '{
    "descriptors": [
      [0.1, -0.2, 0.15, ..., 0.08],  # 128 floats
      [0.12, -0.19, 0.14, ..., 0.09],
      ... (minimal 10 arrays)
    ]
  }'

# 4. Verify di database
mysql -h db -u root -p jez_erp

SELECT u_name, 
       JSON_EXTRACT(u_face, '$.registered_at') as registered_at,
       JSON_LENGTH(u_face, '$.samples') as descriptor_count
FROM users
WHERE id = 1;

# Output: u_name | 2024-04-03T14... | 10
```

---

## Troubleshooting

### ❌ "No face detected"
- **Penyebab**: Gambar terlalu gelap, wajah tidak jelas
- **Solusi**: Improve lighting, posisikan wajah lebih jelas, minimal 20% dari foto

### ❌ "Multiple faces detected"
- **Penyebab**: Ada 2+ orang di frame
- **Solusi**: Hanya 1 orang per foto (orang yang di-register)

### ❌ "Quality score terlalu rendah"
- **Penyebab**: Blur, terlalu jauh, atau sudut tidak bagus
- **Solusi**: Ambil ulang dengan cahaya lebih bagus, dekat ke camera

### ❌ "Face tidak cocok saat absen"
- **Penyebab**: Registration dengan kualitas rendah
- **Solusi**: Re-register dengan 10 sampel berkualitas lebih baik

### ❌ "Database column u_face error"
- **Penyebab**: Column tidak ada atau type salah
- **Solusi**: 
```sql
ALTER TABLE users 
ADD COLUMN u_face LONGTEXT COMMENT 'Face descriptors JSON';
```

---

## Summary

**Registration Flow**:
1. PIC buka app & pilih karyawan
2. Ambil 10+ foto dari berbagai sudut (React Native)
3. Setiap foto: detect wajah → extract descriptor → quality check
4. Upload 10 descriptors ke Laravel
5. Laravel simpan ke jez_erp.users.u_face (JSON)

**Daily Usage**:
1. Karyawan ambil 1 foto wajah
2. App extract 1 descriptor
3. Kirim ke Laravel untuk identify
4. Laravel cari match di 10 stored descriptors
5. Jika match → Attendance recorded ✓

**Database**:
- jez_erp.users.u_face = JSON dengan 10+ descriptors
- Setiap descriptor = array dari 128 floats
- Format: `{"mode": "registration", "samples": [...]}`

Sistem siap production! 🚀
