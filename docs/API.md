# REST API Documentation

All API endpoints are versioned and prefixed with `/api/v1/` unless noted.

---

## 1. Authentication (`/api/v1/auth`)

### POST `/login`
*   **Purpose**: Log in and request session token.
*   **Request**: `{ "email": "str", "password": "str" }`
*   **Response**: `200 OK`
    ```json
    {
      "token": "7a3b4c9e8d1f2a3b...",
      "username": "admin",
      "role": "Admin",
      "expires_at": "2026-07-05T21:30:00Z"
    }
    ```

### POST `/logout`
*   **Headers**: `Authorization: Bearer <token>`
*   **Response**: `200 OK`

### POST `/register`
*   **Access**: Admin only.
*   **Request**: `{ "username": "str", "email": "email", "password": "str", "role": "str" }`
*   **Response**: `201 Created`

---

## 2. Cases (`/api/v1/cases`)

### GET `/`
*   **Response**: `200 OK` (Array of case objects containing originals and matches counts).

### POST `/`
*   **Request**: `{ "title": "str", "description": "str" }`
*   **Response**: `201 Created`

### PUT `/{case_id}`
*   **Request**: `{ "title": "str", "description": "str", "status": "str" }`
*   **Response**: `200 OK`

### DELETE `/{case_id}`
*   **Access**: Admin only.
*   **Response**: `200 OK`

---

## 3. Originals (`/api/v1/originals`)

### GET `/{case_id}`
*   **Response**: `200 OK` (Lists originals associated with case).

### POST `/upload/chunk`
*   **Form Data**: `upload_uuid` (str), `chunk_index` (int), `total_chunks` (int), `file` (binary).
*   **Response**: `200 OK`

### POST `/upload/assemble`
*   **Request**: `{ "case_id": int, "upload_uuid": "str", "filename": "str", "checksum": "str" }`
*   **Response**: `200 OK`

### GET `/{original_id}/frame`
*   **Query Params**: `offset` (float - offset timestamp in seconds).
*   **Response Headers**: `Content-Type: image/jpeg`
*   **Response**: Binary JPEG image stream.

### DELETE `/{original_id}`
*   **Access**: Admin only.
*   **Response**: `200 OK`
