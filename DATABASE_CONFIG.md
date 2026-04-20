# Database Configuration Guide

## Current Setup

The Python Face Recognition backend automatically uses the Laravel API endpoints to sync face data. It doesn't directly access the database, so table naming is handled by Laravel.

### Database Information

- **Database Name**: `jez_erp` ✓
- **Database Host**: `db` (from DB_HOST in .env)
- **Database Port**: `3306`
- **User Table**: `users` (configured in Laravel User model)
- **Face Data Column**: `u_face` (LONGTEXT/JSON)

### Laravel Configuration

The Laravel app (`jez_sistem`) uses:
```php
// app/Models/User.php
protected $table = 'users';
```

And in `.env`:
```
DB_DATABASE=jez_erp
```

## If Using Different Table Names

If your Laravel setup uses a different table name (e.g., `ts_users`), you need to:

1. **Update Laravel Model**:
   ```php
   // app/Models/User.php
   protected $table = 'ts_users';  // Change this if needed
   ```

2. **Update API URL Configuration**:
   - The Python backend communicates via Laravel API (not direct database access)
   - So as long as Laravel API endpoints work, the Python backend will work automatically

3. **Configure Python Backend** (if direct DB access needed in future):
   ```env
   # In .env
   DB_NAME=jez_erp
   DB_TABLE=ts_users  # Adjust if different
   ```

## Verifying Your Database

Check your actual table name:

```bash
# Connect to MySQL
mysql -h db -u root -p jez_erp

# List tables
SHOW TABLES;

# Check if 'users' or 'ts_users' exists
DESCRIBE users;
DESCRIBE ts_users;

# Check u_face column
SHOW COLUMNS FROM users LIKE 'u_face';
```

## Important Notes

- ✅ The Python backend uses **Laravel API endpoints**, not direct database queries
- ✅ As long as Laravel API is working, Python backend works with any table structure
- ℹ️ Table naming doesn't matter for the Python backend - it only matters for Laravel
- ⚠️ If you change table names in Laravel, update Laravel's User model first

## Current API Flow

```
Python Backend
    ↓ (HTTP Requests)
Laravel API (/api/...)
    ↓ (Eloquent ORM)
Database Table (users or ts_users)
    ↓
u_face column (JSON)
```

The Python backend doesn't care about the actual table name - it just calls Laravel API endpoints which handle all database queries.
