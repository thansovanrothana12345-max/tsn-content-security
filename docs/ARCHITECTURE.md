# System Architecture

This document describes the high-level software architecture, data processing flows, and modular divisions of the **Copyright Center**.

---

## 🏛️ High-Level Component Layout

The platform uses a hybrid client-server model embedded within a single native PySide6 desktop wrapper:

```
                  ┌───────────────────────────────┐
                  │        PySide6 Wrapper        │
                  │       (QWebEngineView)        │
                  └──────────────┬────────────────┘
                                 │ HTTP / JSON
                                 ▼
                  ┌───────────────────────────────┐
                  │    FastAPI Server Daemon      │
                  │  (Routes, Auth, Cases, Files) │
                  └──────────────┬────────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 ▼                               ▼
    ┌─────────────────────────┐     ┌─────────────────────────┐
    │     SQLite Registry     │     │ Background Job Worker   │
    │ (Users, Cases, Evidence)│     │  (dHash, FFT Scans)     │
    └─────────────────────────┘     └─────────────────────────┘
```

### 1. PySide6 Shell Launcher (`main.py`)
*   Bootstraps the local environment.
*   Allocates a dynamic port using TCP socket binders.
*   Spawns uvicorn and worker loops in daemon threads.
*   Launches the GUI hosting a web engine view rendering the single-page application.

### 2. FastAPI Backend Engine (`backend/app.py`)
*   Exposes versioned REST API routers.
*   Handles token session registrations, CRUD database mappings, and static file mount paths.

### 3. Background Job Worker (`backend/worker.py`)
*   Monitors tasks inside the database queue.
*   Runs CPU-intensive operations (hashing, stream scraping, FFT transformations, matching alignments) asynchronously, preventing GUI thread blocking.

### 4. Storage Directory
*   Local database file (`storage/database.db`).
*   Original video registry folder (`storage/originals/`) storing uploaded files renamed as unique UUIDs.
*   Evidence screenshot folder (`storage/evidence/`) storing downloaded thumbnails and side-by-side verification proofs.
