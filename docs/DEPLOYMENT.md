# Deployment Manual - TSN Copyright Defender

This document lists requirements, environment configurations, folder permissions, and service launches for production environments.

---

## 1. Runtime Pre-requisites
- **Python**: Python 3.10+
- **Database Engine**: Local SQLite (SQLite3 included in Python binary distribution)
- **External Binaries**: `ffmpeg` (for frame seeks and metadata audio parsing)

---

## 2. Directory Layout & Permissions
Ensure these directories are present at the application root:
- `storage/` (main storage mount)
- `storage/originals/` (uploaded reference files)
- `storage/evidence/` (downloaded screenshots/thumbnails)
- `storage/temp/` (multipart uploads chunks buffer)
- `storage/logs/` (rotating logs destination)

Linux permission setups:
```bash
mkdir -p storage/{originals,evidence,temp,logs}
chmod -R 775 storage
```

---

## 3. Environment Environment Configurations (`.env`)
Create a `.env` file at the root folder:
```bash
APP_ENV=production
APP_PORT=8000
DATABASE_URL=storage/database.db
STORAGE_DIR=storage
SECRET_KEY=use_your_32_byte_secure_hex_token
DEVELOPMENT_BYPASS_AUTH=False
```

---

## 4. Run Process Services

### A. API Server Daemon
Start Uvicorn server processes inside a background manager (e.g. systemd, PM2, or supervisor):
```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000 --workers 4
```

### B. Background Task Worker
Execute the background task manager script in a loop service:
```bash
python -m backend.worker
```

---

## 5. Log Troubleshooting
- Access the rotating logs for system alerts and failures:
  ```bash
  tail -f storage/logs/app.log
  ```
- Liveness monitoring:
  ```bash
  curl http://localhost:8000/health
  curl http://localhost:8000/metrics
  ```
