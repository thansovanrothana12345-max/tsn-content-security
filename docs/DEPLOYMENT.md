# Deployment & Build Guide

This document describes how to compile the native desktop wrapper, configure production directories, and run database backups.

---

## 1. PyInstaller Build Steps
To package the PySide6 app and FastAPI backend as a single standalone executable on Windows:

1.  Install PyInstaller:
    ```bash
    pip install pyinstaller
    ```
2.  Build the executable using the spec configuration or CLI flags (bundle static frontend assets and binary templates):
    ```bash
    pyinstaller --noconsole --name="CopyrightCenter" \
      --add-data "frontend/static;frontend/static" \
      --add-data "storage/templates;storage/templates" \
      main.py
    ```
3.  The compiled executable will be located in the `dist/CopyrightCenter/` directory.

---

## 2. Directory Configurations
Ensure the environment directories have correct user access privileges in production:
*   `storage/originals/`: Read/Write access (restricted to application process user).
*   `storage/evidence/`: Read/Write access (restricted to application process user).
*   `storage/database.db`: Enforce write permissions.

---

## 3. Database Backups
*   **Method**: Utilize SQLite's Online Backup API or copy the file directly:
    ```powershell
    Copy-Item -Path "storage/database.db" -Destination "backup/database_$(Get-Date -Format 'yyyyMMdd_HHmmss').db"
    ```
*   **Frequency**: Recommended daily rotation.
