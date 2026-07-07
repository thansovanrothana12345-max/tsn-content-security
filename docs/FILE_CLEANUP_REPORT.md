# File Cleanup Report - TSN Copyright Defender

This document identifies redundant, duplicate, obsolete, and temporary files in the repository and provides recommendations for archival, renaming, and general project hygiene.

---

## 1. Duplicate Files Identified
- **`main​​​ 2.py`** (Root): Duplicate clone of `main.py`.
  - *Recommendation*: **Archived**. Successfully relocated to `archive/main 2.py`.
- **`main​​​ 3.py`** (Root): Duplicate launcher script with configured port parameters.
  - *Recommendation*: **Archived**. Successfully merged its port configuration logic into `main.py` and relocated the file to `archive/main 3.py`.

---

## 2. Temporary & Obsolete Scratch Files
The `scratch/` directory contains numerous helper scripts from development phases. We recommend moving the following files to `archive/` or a dedicated subfolder to keep the workspace clean:
- **`app.js.fixed`**: Development copy of frontend JS. (Archive).
- **`run_main3_headless.py`**: Headless desktop test module. (Archive).
- **`test_main3_startup.py`**: Temporary launcher script test. (Archive).
- **`verify_register_public.py`**: Verification script for registration public access check. (Archive).
- **`reproduce_upload_failure.py`**: Development failure investigator. (Archive).
- **`repair_admin.py`**: Seed recovery helper. (Archive).
- **`test_gui.py`**: Temporary PySide validation UI. (Archive).
- **`benchmark_phase3.py`**: Development phase latency benchmark. (Archive).
- **`test_evidence.jpg`**: Infringing test asset image sample. (Keep under `scratch/` or move to a `tests/fixtures/` directory).

---

## 3. Recommended Renames
To improve readability and conform to Python snake_case conventions:
- **`CopyrightCenter.spec`** (Root) -> **`copyright_center.spec`**
- **`docs/ADMIN_GUIDE.md`** -> **`docs/ADMIN_MANUAL.md`**
- **`docs/USER_GUIDE.md`** -> **`docs/USER_MANUAL.md`**
- **`docs/ROADMAP.md`** -> **`docs/PROJECT_ROADMAP.md`**

---

## 4. Empty Folders
- No completely empty directories were found. The standard directories (`backend/`, `frontend/`, `storage/`, `tests/`) contain active production components.

---

## 5. Dependency Observations
- There is currently no `requirements.txt` manifest at the repository root. Setting up an explicit `requirements.txt` with specific pinned versions (e.g. `fastapi==0.111.0`, `PySide6==6.7.1`, `yt-dlp>=2024.5.27`, `pytest==9.1.1`) is recommended to ensure reproducible builds across machines.
