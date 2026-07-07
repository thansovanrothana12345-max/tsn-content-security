# Admin Manual - TSN Copyright Defender

This manual provides administrators with guidelines for user management, system audit logging, database health tuning, and logs troubleshooting.

---

## 1. User Management & Registration
1. **Access Level**: Only accounts with the `Admin` role can register new users.
2. **Standard Roles**:
   - `Admin`: Full write, delete, user creation, and audit logging access.
   - `Editor`: Standard case creation, file uploading, and notice generation.
   - `Reviewer`: Reads timeline events, appends audit notes, and updates statuses.
   - `Guest`: Read-only access to Dashboards, listings, and attachments.
3. **Registration Endpoint**:
   - Access user registration from `/api/v1/auth/register` to provision editor/reviewer scopes safely.

---

## 2. Audit Trails & Compliance logs
- Every sensitive operation (user login, asset uploads, case deletions, and DMCA creations) logs an entry to the `audit_logs` table.
- **Audit Viewer**:
  - Navigate to the Admin Center in the GUI to filter audit lists by action (e.g. `LOGIN`, `DELETE_CASE`) or user ID.

---

## 3. Database Maintenance
SQLite databases operate best when vacuumed and optimized periodically:
- **Clean sessions**: Clean up expired stateful login tokens periodically using SQL queries:
  ```sql
  DELETE FROM sessions WHERE expires_at < CURRENT_TIMESTAMP;
  ```
- **DB Compacting**:
  ```sql
  VACUUM;
  ```
- **Integrity Check**: Run this periodically to ensure index tables are correct:
  ```sql
  PRAGMA integrity_check;
  ```

---

## 4. Troubleshooting & Logging
- Service metrics are accessible at `/metrics`. Check `scan_jobs` statuses to identify if background workers are lagging.
- Structured application log trails are written to `storage/logs/app.log`. Look out for `[BACKGROUND_WORKER] [STATUS=ERROR]` prefixes to identify extractor or network timeout events.
