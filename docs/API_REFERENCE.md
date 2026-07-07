# API Reference - TSN Copyright Defender

This document lists all active REST API endpoints, user access levels, request payloads, and response models.

---

## 1. Authentication & Sessions (`/api/v1/auth` & `/api/auth`)

- **`POST /api/auth/login`**
  - **Access**: Public
  - **Payload**: `{"username": "admin", "password": "AdminPassword123"}`
  - **Response**: `{"token": "JWT_TOKEN_STRING", "user": {"id": 1, "username": "admin", "role": "Admin"}}`
- **`POST /api/v1/auth/logout`**
  - **Access**: Authenticated Session
  - **Response**: `{"message": "Logged out successfully"}`
- **`POST /api/v1/auth/register`**
  - **Access**: `Admin` only
  - **Payload**: `{"username": "editor1", "email": "ed@local.com", "password": "Password123", "role": "Editor"}`
  - **Response**: User object (201 Created)

---

## 2. Asset Library (`/api/v1/assets`)

- **`POST /api/v1/assets`**
  - **Access**: `Admin`, `Editor`
  - **Payload**: Multipart Form (`case_id` int, `asset_type` string, `file` UploadFile)
  - **Limits**: Maximum 50MB file size.
  - **Response**: `{"id": 1, "sha256_hash": "...", "status": "Active"}` (201 Created)
- **`GET /api/v1/assets`**
  - **Access**: Any Authenticated User
  - **Parameters**:
    - `case_id` (integer, optional)
    - `asset_type` (string, optional)
    - `limit` (integer, default 50, max 200)
    - `offset` (integer, default 0)
    - `sort_by` (string, default "upload_date")
    - `order` (string, default "DESC")
  - **Response**: List of Asset objects.

---

## 3. Scan Center (`/api/v1/scans`)

- **`POST /api/v1/scans`**
  - **Access**: `Admin`, `Editor`, `Reviewer`
  - **Payload**: `{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "case_id": null}`
  - **Response**: `{"job_id": 12, "status": "Pending", "message": "Scan job successfully queued."}` (202 Accepted)
- **`GET /api/v1/scans/{job_id}/status`**
  - **Access**: Any Authenticated User
  - **Response**: `{"id": 12, "url": "...", "status": "Running", "progress_percent": 30.0, "error_message": null}`
- **`GET /api/v1/scans/results`**
  - **Access**: Any Authenticated User
  - **Parameters**: `job_id`, `platform`, `limit`, `offset`, `sort_by`, `order`

---

## 4. Evidence Ledger (`/api/v1/evidence`)

- **`POST /api/v1/evidence/create`**
  - **Access**: `Admin`, `Editor`
  - **Payload**: `{"scan_result_id": 15, "case_id": 4}`
  - **Response**: Promoted Evidence object.
- **`POST /api/v1/evidence/attach`**
  - **Access**: `Admin`, `Editor`
  - **Payload**: `{"evidence_id": 8, "case_id": 4}`
- **`GET /api/v1/evidence/view/{evidence_id}`**
  - **Access**: Any Authenticated User
  - **Response**: Full evidence details, associated cases, upload attachments, and historical audit timeline records.

---

## 5. Health & Monitoring

- **`GET /health`**
  - **Access**: Public
  - **Response**: `{"status": "healthy"}`
- **`GET /ready`**
  - **Access**: Public
  - **Response**: `{"status": "ready"}` (Returns 503 if DB locked/offline)
- **`GET /metrics`**
  - **Access**: Public (Or restricted)
  - **Response**: Job counts summary, asset counts, evidence counts, and disk size in MB.
```json
{
  "status": "online",
  "scan_jobs": {"Pending": 2, "Running": 0, "Completed": 10, "Failed": 1, "Cancelled": 0},
  "total_assets": 8,
  "total_evidence": 15,
  "storage_size_mb": 14.5
}
```
