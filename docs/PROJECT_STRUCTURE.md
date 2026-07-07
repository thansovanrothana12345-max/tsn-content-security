# Project Structure - TSN Copyright Defender

This document outlines the folder hierarchy, module layout, entry points, and database file structures of the platform.

---

## 1. Folder Hierarchy

```
TSN Content Security/
├── archive/                  # Archival directory for duplicate and obsolete development files
├── backend/                  # Python backend application layer
│   ├── ai/                   # Modular similarity matching model hooks (Video, Image, Audio)
│   ├── routes/               # API route sub-controllers (auth, cases, health, evidence, etc.)
│   ├── services/             # Domain logic (Connectors, URL validator, AI interfaces, Logging)
│   ├── app.py                # FastAPI app initialization and global middlewares
│   ├── config.py             # Configuration parameters and whitelisted environment settings
│   ├── database.py           # SQLite connection pools and table schema migrations
│   ├── downloader.py         # Subprocess stream scraping helpers
│   ├── fingerprint.py        # File hashing and audio signature extraction
│   └── worker.py             # Background task queue polling engine
├── docs/                     # Architectural manuals and deployment specifications
├── frontend/                 # Static user interface assets
│   └── static/
│       ├── css/              # Tailwind and Vanilla responsive layouts
│       ├── js/               # Single Page Application controller (app.js)
│       └── index.html        # HTML shell wrapper
├── storage/                  # Persistent data directory
│   ├── database.db           # SQLite database engine
│   ├── originals/            # Registered source video reference files
│   ├── evidence/             # Downloaded proof details and screenshots
│   └── logs/                 # Rotating audit log appenders
├── tests/                    # Core pytest test modules
└── main.py                   # PySide6 Chromium GUI native wrapper (Production Entrypoint)
```

---

## 2. Core Entry Points
- **Desktop Client (`main.py`)**: Spawns FastAPI, initiates the background worker daemon, and wraps the HTML frontend inside a Chromium QWebEngineView frame.
- **Backend API (`backend/app.py`)**: Configures Uvicorn server middleware, mounts static files, and routes endpoints.

---

## 3. Core Modules & Systems

### A. Authentication & Session Manager (`auth.py`)
- Employs signed JWT assertions cross-checked with active records in the `sessions` table.
- Restricts privileged endpoints via Role-Based Access Controls (RBAC) validations.

### B. Connector & Scan Engine
- Resolves web target streams using isolated connector modules (YouTube, Instagram, TikTok, Facebook).
- Spawns background tasks to extract metadata, download low-res clips, capture snapshots, and log progress.

### C. Registry Ledger (`database.py`)
- Executes SQLite queries using Write-Ahead Logging (WAL) concurrency optimizations.
- Deploys startup migrations creating table indexers (`sha256_hash` search matches, junction maps).

---

## 4. Systems Data Flow

```
User URL Submission (UI) 
  --> FastAPI Endpoint (scans_router) 
  --> SQL queue write (scan_jobs status: Pending) 
  --> Worker Poll (worker_loop)
  --> Connector Resolution (get_connector_for_url) 
  --> Platform Metadata Scraper & screenshot download
  --> DB promotion (evidence status: Detected)
  --> UI refresh poll status
```
