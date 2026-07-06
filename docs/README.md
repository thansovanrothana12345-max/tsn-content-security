# Copyright Center

AI-Powered Copyright Protection & Evidence Management Platform.

---

## 🚀 Overview
The **Copyright Center** is a secure, local-first enterprise desktop application designed to track video leaks across media sharing sites. It extracts perceptual visual and acoustic fingerprints from original works and automatically matches crawled links to log infringing evidence, output DMCA notice drafts, and compile detailed audits.

---

## 🛠️ Prerequisites & Installation

### 1. System Dependencies
*   **Python**: Version 3.10 or higher.
*   **FFmpeg**: Required on the system PATH to support audio demuxing and acoustic peak extractions.

### 2. Python Dependencies
Install required libraries:
```bash
pip install fastapi uvicorn PySide6 opencv-python-headless numpy pydantic email-validator python-multipart httpx
```

### 3. Folder Layout
Create the local storage structure:
```
storage/
  ├── database.db     # SQLite Registry
  ├── originals/      # Original videos
  ├── evidence/       # Screenshots & proofs
  └── temp/           # Temporary download caches
```

---

## 🖥️ Running the Application

To boot both the FastAPI backend daemon and the PySide6 native desktop wrapper:
```bash
python main.py
```
This automatically:
1.  Allocates an open port dynamically to avoid connection collisions.
2.  Launches the FastAPI server in a background thread.
3.  Initializes the database worker queue polling thread.
4.  Launches the native QWebEngineView wrapper pointed at the server address.
