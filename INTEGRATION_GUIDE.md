# Complete Integration Guide for Face Recognition Attendance System

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  React Native Mobile App (face-id)                          │
│  - Camera capture                                           │
│  - Face detection                                           │
│  - Extract face descriptors                                 │
│                ↓                                             │
│         HTTP POST                                           │
│                ↓                                             │
│  Laravel Backend (jez_sistem)                               │
│  - Face identification                                      │
│  - Attendance recording                                      │
│  - Database storage                                         │
│  - User authentication                                      │
│       ↙         ↘                                           │
│      ↙           ↘                                          │
│ MySQL DB      Python Backend (optional)                     │
│ Face data    - Alternative face recognition                │
│ Attendance   - Batch processing                             │
│              - Quality assessment                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. React Native App (Mobile Client)
- **Location**: `/home/royyan/projects/face-id`
- **Function**: Captures faces using device camera
- **Technology**: React Native with Vision Camera

### 2. Laravel Backend (Web Server)
- **Location**: `/home/royyan/projects/jez_sistem`
- **Function**: 
  - API for mobile app
  - Face identification/matching
  - Attendance/presence recording
  - User management
  - Data storage and retrieval
- **Technology**: Laravel PHP Framework

### 3. Python Face Recognition Backend (Optional)
- **Location**: `/home/royyan/projects/face-attendance-ai`
- **Function**:
  - Alternative face recognition engine
  - Face encoding and matching
  - Quality assessment
  - Server-side face processing
- **Technology**: FastAPI, Python face-recognition library

## Setup Instructions

### Prerequisites
- Python 3.8+
- Node.js 14+
- Laravel 8+
- MySQL 5.7+

### Step 1: Setup Python Face Recognition Backend

```bash
# Navigate to project
cd /home/royyan/projects/face-attendance-ai

# Run setup script
chmod +x setup.sh
./setup.sh

# Configure environment
cp .env.example .env
# Edit .env and update:
# - LARAVEL_API_URL (where your Laravel app is running)
# - FACE_MATCH_THRESHOLD (0.6 recommended)

# Start the server
chmod +x start.sh
./start.sh
```

Server will run on `http://localhost:8000`

### Step 2: Verify Laravel Backend

1. Ensure Laravel app is running
2. Check face-related database tables:
   - `users` table with `u_face` column (JSON format)
   - `attendance` table for records
   - Create migration if needed:

```php
// database/migrations/xxxx_add_face_columns.php
Schema::table('users', function (Blueprint $table) {
    $table->longText('u_face')->nullable()->comment('face recognition data JSON');
});
```

### Step 3: Configure React Native App

Update API endpoint in [/src/services/mobileApi.ts](../face-id/src/services/mobileApi.ts):

```typescript
const API_BASE_URL = "https://your-laravel-domain.com/api";
// or for local development:
const API_BASE_URL = "http://192.168.x.x:8000/api";  // Use your machine IP
```

### Step 4: Build and Run React Native App

```bash
cd /home/royyan/projects/face-id

# Install dependencies
npm install

# Run on Android
npm run android

# Or iOS
npm run ios
```

## API Workflows

### Workflow 1: User Face Registration (PIC - Picture In Charge)

```
1. PIC opens app and logs in
   POST /api/login

2. PIC selects employee from list
   GET /api/v1/mobile/pic/users?search=...

3. PIC opens camera and captures face samples (10+ times)
   - Each capture sends descriptor to bridge
   
4. When enough samples collected:
   POST /api/v1/mobile/pic/users/{userId}/face
   {
     "descriptors": [
       [0.1, -0.2, 0.15, ...],  // 128 floats per descriptor
       [0.05, -0.18, 0.12, ...],
       ...
     ]
   }

5. Laravel stores in `ts_users.u_face` JSON column:
   ```json
   {
     "mode": "registration",
     "samples": [
       { "descriptor": [...], "timestamp": "2024-04-03T..." },
       ...
     ],
     "registered_at": "2024-04-03T..."
   }
   ```
```

### Workflow 2: Daily Attendance Check-in

```
1. Employee opens app (public/login page)
   
2. Employee taps "Scan Face for Attendance"
   
3. App opens camera and captures one face image
   
4. Face detection extracts descriptor (128 floats)
   
5. App sends to identification endpoint:
   POST /api/v1/mobile/public/attendance/identify
   {
     "face_descriptor": [0.1, -0.2, 0.15, ...]
   }

6. Laravel matches against all registered users:
   - Compare with each user's stored descriptors
   - Find best match
   - Return matched user

7. If match found:
   GET /api/v1/mobile/attendance/today
   
8. Record attendance:
   POST /api/v1/mobile/attendance/submit
   {
     "photo": "data:image/jpeg;base64,...",
     "lokasi": "POINT(-7.945 112.619)",
     "alamat": "Office Location",
     "gps_accuracy": 10.5,
     "gps_speed": 0.0,
     "face_descriptor": [...]
   }
```

### Workflow 3: Python Backend Processing (Optional)

```
1. Get all users' face data:
   GET http://localhost:8000/api/faces/sync
   
2. Check face image quality:
   POST http://localhost:8000/api/faces/quality
   {
     "image_data": "data:image/png;base64,..."
   }
   
3. Encode face from image:
   POST http://localhost:8000/api/faces/encode
   {
     "image_data": "data:image/png;base64,..."
   }
   
4. Identify user via Python:
   POST http://localhost:8000/api/faces/identify
   {
     "image_data": "data:image/png;base64,..."
   }
```

## Database Schema

### Database & Table Information
- **Database**: `jez_erp`
- **Table**: `users`
- **Face Column**: `u_face` (LONGTEXT)

### users Table - Face Data (JSON) in u_face Column

```json
{
  "mode": "registration",
  "registered_at": "2024-04-03T10:30:00Z",
  "samples": [
    {
      "id": "sample_1",
      "descriptor": [0.1, -0.2, 0.15, ...],  // 128 floats
      "timestamp": "2024-04-03T10:30:00Z"
    }
  ],
  "photo_samples": [
    {
      "id": "photo_1",
      "path": "faces/user_id/photo_1.jpg",
      "timestamp": "2024-04-03T10:31:00Z"
    }
  ]
}
```

### Attendance Record

```json
{
  "id": 1,
  "user_id": 15,
  "at_date": "2024-04-03",
  "at_time_in": "08:30:00",
  "at_time_out": "17:00:00",
  "at_location_in": "POINT(-7.945 112.619)",
  "at_location_out": "POINT(-7.945 112.619)",
  "at_photos_in": "attendance/15/att_15_20240403_083000.jpg",
  "at_photos_out": "attendance/15/att_15_20240403_170000.jpg",
  "at_status": "present",
  "at_notes": "Face verified. Best distance: 0.3245"
}
```

## Configuration Parameters

### Laravel Configuration
Edit `config/face_recognition.php`:

```php
return [
    'match_threshold' => 0.6,  // 0.0 - 1.0 (higher = stricter)
    'top_k_samples' => 3,      // How many closest matches to average
    'average_top_k_threshold' => 0.4,
];
```

### Location Verification
Edit `config/location_verification.php`:

```php
return [
    'center_lat' => -7.945,
    'center_lng' => 112.619,
    'radius_meters' => 100,
    'geofence_enabled' => true,
    'anti_fake_gps_enabled' => true,
];
```

### Python Configuration
Edit `.env`:

```env
HOST=0.0.0.0
PORT=8000
DEBUG=true
LARAVEL_API_URL=http://localhost:8000/api
FACE_MATCH_THRESHOLD=0.6
```

## Troubleshooting

### Issue: "No face detected"
- **Cause**: Image quality, poor lighting, or no clear face
- **Solution**: Ensure face is clear and well-lit, face should be at least 20% of image size

### Issue: "Face match confidence too low"
- **Cause**: Not enough registration samples or poor quality samples
- **Solution**: Register user with more samples in different poses/angles

### Issue: "Connection refused" 
- **Cause**: Services not running or wrong API URL
- **Solution**: Check if Laravel and Python servers are running, verify API URLs

### Issue: Low attendance accuracy
- **Cause**: Lighting changes, face registrations in different conditions
- **Solution**: Re-register users with samples from the actual attendance location/lighting

## Performance Tips

1. **Caching**: Cache face data in Laravel to reduce database queries
2. **Batch Processing**: Pre-load all users' face descriptors at startup
3. **Image Compression**: Compress images before sending to reduce bandwidth
4. **Descriptor Caching**: Cache computed descriptors for 5-10 minutes

## Security Considerations

1. **HTTPS Only**: Always use HTTPS in production
2. **API Authentication**: Use Bearer tokens for API access
3. **Face Data Privacy**: Encrypt face descriptors in database
4. **Rate Limiting**: Implement rate limiting on attendance endpoints
5. **CORS**: Configure CORS properly for mobile/web clients

## Support & Monitoring

### Check Server Health
```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/status
```

### View Logs
```bash
# Laravel logs
tail -f /home/royyan/projects/jez_sistem/storage/logs/laravel.log

# Python logs
tail -f /home/royyan/projects/face-attendance-ai/logs/*.log
```

### Monitor Database
```bash
# Check face registration count
SELECT u_name, 
       JSON_EXTRACT(u_face, '$.samples') as sample_count
FROM users WHERE u_face IS NOT NULL;

# Check attendance records
SELECT DATE(at_date), COUNT(*) as total
FROM attendance
GROUP BY DATE(at_date);
```

## Next Steps

1. Test face registration with a sample user
2. Verify face identification accuracy
3. Implement location verification
4. Setup monitoring and logging
5. Deploy to production with proper SSL/TLS
6. Create user documentation
7. Train staff on usage

## Files Modified/Created

- ✅ `/home/royyan/projects/face-attendance-ai/` - Complete Python backend
- ✅ `/home/royyan/projects/face-id/App.tsx` - Existing React Native integration
- ✅ `/home/royyan/projects/jez_sistem/app/Http/Controllers/Api/MobileAttendanceController.php` - Existing endpoints
- ⚠️ May need to create: Database migrations for face data if not present

## Support

For issues or questions:
1. Check logs in both Laravel and Python services
2. Verify network connectivity between services
3. Test endpoints using curl or Postman
4. Review console output in React Native app

