# Admin Management Manual

This manual details administrator configurations, user additions, role setups, and compliance logs audits.

---

## 1. Creating User Accounts
Only users with the **Admin** role can create accounts:
1.  Navigate to **System settings** on the sidebar.
2.  Select **User Management**.
3.  Click **Add User**.
4.  Input details, select target role, and save.

### Roles and Permissions Matrix
*   **Admin**: Full read/write access, database backups, user additions.
*   **Editor**: Create cases, upload originals, trigger scans, edit data.
*   **Reviewer**: Read cases, trigger scans, edit matching statuses.
*   **Guest**: Read-only case listings (no additions or scanner actions).

---

## 2. Reviewing Audit Log Trails
To audit system compliance:
1.  Go to the **System Logs** view.
2.  The audit list displays:
    *   **Timestamp**: ISO time.
    *   **User**: Operator name.
    *   **Action**: Operations executed (e.g. `LOGIN`, `UPLOAD_ORIGINAL`, `DELETE_CASE`).
    *   **IP Address**: Client loopback IP.
    *   **Details**: Before/After changes JSON states.

---

## 3. Database Maintenance & Backups
*   **Database File**: Stored locally at `storage/database.db`.
*   **Backup Action**: Make a copy of the database file when the server is idle.
*   **Restore**: Replace `storage/database.db` with the backup file and restart the application launcher.
