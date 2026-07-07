# System Architecture - TSN Copyright Defender

This document describes the high-level software architecture, data processing flows, modular divisions, and platform integration designs.

---

## 1. High-Level Component Layout

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
    │ (Users, Cases, Evidence)│     │ (Platform Connectors)   │
    └─────────────────────────┘     └─────────────────────────┘
```

### A. PySide6 Shell Launcher (`main.py`)
- Allocates an unused TCP port dynamically on startup.
- Spawns Uvicorn (FastAPI) and the background worker loop in daemon threads.
- Hosts a native window shell rendering the Chromium SPA frontend.

### B. FastAPI Web Controller (`backend/app.py`)
- Exposes versioned routing modules.
- Enforces Role-Based Access Controls (RBAC) and stateful token expiration checks.
- Manages standard JSON error responses and whitelisted search parameters.

### C. Background Worker Loop (`backend/worker.py`)
- Continuously polls `scan_jobs` and `background_jobs` tables.
- Runs heavy URL scraping, image capture, and file assembly tasks asynchronously to keep the UI smooth.

---

## 2. Connector Layer (Platform-Specific Scrapers)

To isolate platform-specific scraping and extraction behaviors, the platform integrates a modular Connector Layer under `backend/services/connectors/`:

```
               BaseConnector (Abstract Interface)
             ┌───────────┼───────────┼───────────┐
             ▼           ▼           ▼           ▼
         YouTube     TikTok      Instagram   Facebook (Post / Ad Lib)
```

- Each connector implements:
  - `validate(url)`: Pattern checks resolving if a URL domain is supported.
  - `extract_metadata(url)`: Parses titles, creators, and upload dates.
  - `download_screenshot(url)`: Fetches thumbnails/screenshots.
  - `download_asset(url)`: Downloads low-res files for fingerprinting comparisons.

---

## 3. Observability & Monitoring

### A. Structured Logging
The system exposes structured log patterns via `backend/services/logger.py` mapping unified prefixes to stdout and files (`storage/logs/app.log`):
- `[SCAN_JOB]`: Tracks start, success, and errors for URL checks.
- `[EVIDENCE]`: Tracks formal evidence creation and case mapping events.
- `[BACKGROUND_WORKER]`: Tracks queue states and polling loops.
- `[CONNECTOR]`: Tracks scraping attempts, retries, and downstreams.
- `[API_ERROR]`: Tracks unhandled Web API exceptions.

### B. Health Probes
- `/health`: Liveness probe.
- `/ready`: Inspects SQLite database connectivity.
- `/metrics`: Displays job counts by status, asset numbers, and storage disk sizes.
