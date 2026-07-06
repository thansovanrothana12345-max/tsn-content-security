# Security Configuration Guidelines

This document details the security systems, access controls, password hashing, and input validation configurations of the **Copyright Center**.

---

## 1. Role-Based Access Control (RBAC)

The backend enforces endpoint access using FastAPI dependency injects verifying token claims against a permissions matrix:

| User Role | Manage Users | System Settings | Create Cases | Upload Originals | Execute Scans | Read-Only |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Admin** | Yes | Yes | Yes | Yes | Yes | Yes |
| **Editor** | No | No | Yes | Yes | Yes | Yes |
| **Reviewer** | No | No | No | No | Yes | Yes |
| **Guest** | No | No | No | No | No | Yes |

```python
# Authorization token verify function
def require_role(allowed_roles: list[str]):
    def dependency(user: dict = Depends(get_current_user)):
        if user["role"] not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden")
        return user
    return dependency
```

---

## 2. Password Hashing & Seeding
*   Passwords are encrypted using SHA-256 (with salted configurations) before database insertion.
*   Baseline database migrations seed a default system administrator on startup (if `users` table is empty):
    *   **Username**: `admin`
    *   **Password**: `AdminPassword123`

---

## 3. Input Sanitization & Traversal Mitigation
*   **Filename Sanitization**: Upload filenames are scrubbed to strip characters outside alphanumeric ranges, dashes, and periods to block directory traversal attacks (e.g. `../../etc/passwd`).
*   **File UUID naming**: Assembled media is renamed using random UUIDv4 names (e.g. `storage/originals/550e8400-e29b-41d4-a716-446655440000.mp4`), neutralizing naming conflict exploits.
*   **Parameterized Queries**: SQLite database calls use parameter placeholders (`?`) to prevent SQL injections.
