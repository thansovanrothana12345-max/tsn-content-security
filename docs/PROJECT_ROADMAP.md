# Project Development Roadmap - TSN Copyright Defender

This document outlines the milestones, completed phases, and upcoming feature sprints for the **TSN Copyright Defender** platform.

---

## 1. Complete Epics & Milestones

### Epic 1: Architecture & UI Foundation
- [x] PySide6 native wrapper window launcher shell with browser engine initialization.
- [x] FastAPI REST routing engine and whitelisted JWT security parameters.
- [x] Responsive layout refactoring (supporting breakpoints from 1920px down to 320px, tablet collapsible sidebars, and card transformations).

### Epic 2: Core Scanning & URL Processing
- [x] Platform connector abstraction layer (YouTube, TikTok, Instagram, Facebook).
- [x] Asynchronous background task polling worker engine executing url fetches.
- [x] Dynamic database schema migrations (assets, scan_results, case_evidence bridge maps).

### Epic 3: Verification & Evidence Ledger
- [x] Structured evidence timeline page mapping audit logs history logs.
- [x] Export zip case utility packaging timeline rows, notes, and attachment proofs.
- [x] PDF & DOCX DMCA notices generation engines.

### Epic 4: Hardening & Stabilization
- [x] Exponential backoff retry policies for temporary connector timeouts.
- [x] Database query latency optimizations (~12x latency drop using index optimizations).
- [x] Standardized API paginations, error tracking loggers, and health check endpoints.

---

## 2. Upcoming Sprints

### Sprint: AI Similarity & Fingerprint Engine Integration
- **Objective**: Implement active comparison models matching enqueued evidence records against registered originals.
- **Key Tasks**:
  - Implement video frame sequence embedding checks conforming to `VideoSimilarityInterface`.
  - Implement CLAHE-normalized image hashing comparisons for enqueued screenshot images.
  - Integrate acoustic peak-to-peak FFT hashing matching audio streams against source registries.
  - Implement OCR text searches on screenshots.

### Sprint: Cloud Scale-out & PostgreSQL Migration
- **Objective**: Move from single-user desktop packaging to scale-out client-server cloud installations.
- **Key Tasks**:
  - Replace local SQLite backend connection pool with PostgreSQL connection managers.
  - Transition connector scraper tasks to distributed Celery/Redis container workers.
  - Package deployment systems under standardized Helm/Kubernetes manifests.
