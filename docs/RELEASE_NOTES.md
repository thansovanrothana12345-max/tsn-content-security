# Release Notes — Copyright Center

This document outlines the major updates and features completed in the current alpha and beta releases.

---

## 🚀 Version v1.0.0-rc.1 (Authentication, Speed Optimizations & Production Build)
*   **Secure JWT Authentication (Phase 1 & 2)**: Standardized all REST endpoints under `/api/v1/` routing. Migrated session tracking to cryptographically signed HMAC-SHA256 JSON Web Tokens. Added local storage session persistence and global interceptors.
*   **User Registration & Admin Controls**: Implemented a full-screen modern authentication overlay and added User Registration forms in the Settings tab, visible and accessible only to Admin accounts.
*   **Similarity Matcher Speedups (Phase 3)**: Optimized image difference hashing (dHash) to run linear interpolation (reducing resize latency from 4.88 ms to 0.002 ms) and vectorized bytecode shifts using NumPy bit-packing.
*   **Sliding Alignments pre-conversion**: Pre-converts visual hex hashes to 64-bit integers to run fast CPU-native integer XOR alignments in the similarity matching loops.
*   **Packaged Installer**: Developed a PyInstaller specs configuration and patched standard modulegraph instruction scans to cleanly bundle the entire server and PySide6 browser application framework into a standalone binary.

---

## 🚀 Version v1.0.0-beta.11 (DMCA Draft Notice Templates)
*   **Notice templates configuration**: Formulates five platform-specific compliant templates: Standard DMCA, YouTube Notice, TikTok IP Report, Meta Rights Complaint, and Cease-and-Desist letter.
*   **Conformed drawing signature canvas**: Captures real-time digital signature pen-strokes as base64 data streams in the client browser UI.
*   **PDF Exporter engine**: Compiles and exports print-ready compliant PDF notices incorporating Case details, original references, side-by-side evidence screenshots, and signature images.
*   **DOCX Exporter engine**: Compiles and exports Microsoft Word formats saving files to downloads with integrated data tables.

---

## 🚀 Version v1.0.0-beta.10 (Audit Log Viewer & Permission Model Access)
*   **Paginated Audit Trail Reader**: Exposes paginated endpoints for system logs access, locked strictly to Admin roles.
*   **Role permissions checks**: Provides dynamic lookup maps (`/roles/me`) for active sessions permissions verifications.
*   **Append-only system integrity**: Restricts database routes to block modifying or deleting historical audit log entries.
*   **REST API controllers**: Exposes endpoints under `/api/v1/auth` prefix for user role details checks and system audit retrievals.

---

## 🚀 Version v1.0.0-beta.9 (Case Archival & Export Package)
*   **Case ZIP compiler downloads**: Bundles metadata, notes annotations, timelines, and physical attachments inside zipped streams.
*   **Database Archival transfers**: Moves closed case folders records to dedicated historical database tables `archived_cases`.
*   **Disk cleanup sweep logic**: Cleans physical disk files copies of attachments on case folder archival.
*   **REST API controllers**: Exposes endpoints under `/api/v1/cases` prefix for downloading ZIP packages and archiving folders.

---

## 🚀 Version v1.0.0-beta.7 (Case Search & Annotation Logs)
*   **Fuzzy metadata search engines**: Parameterized fuzzy matching checks case title, description, or tags fields avoiding SQL injections.
*   **Input HTML tag filters**: Auto-sanitizes annotation text inputs to prevent XSS script executions.
*   **Chronological notes listing**: Retrieves chronological notes mapping badge author usernames directly.
*   **REST API controllers**: Exposes endpoints under `/api/v1/cases` prefix for search queries, annotations logging, and listing notes.

---

## 🚀 Version v1.0.0-beta.5 (Evidence Repository)
*   **Allowed format constraints**: Restricts binary document uploads to secure formats lists (`pdf`, `png`, `jpg`, `jpeg`, `zip`) preventing script executions.
*   **Path traversal sandboxing**: Restricts target file writes to exist strictly within the attachments storage subdirectories.
*   **Cascade and manual cleanups**: Integrates database cascade removal and physical disk files cleanup routines on attachments deletes.
*   **REST API controllers**: Exposes endpoints under `/api/v1/evidence` prefix for uploading, listing, downloading, and deleting files.

---

## 🚀 Version v1.0.0-beta.3 (Case Management)
*   **Workflow State transitions**: Exposes status workflows (Active, Resolved, Closed, Suspended). Only Admins/Editors can edit cases details and link files.
*   **Decoupled user assignments**: Links owner and assignee references to user accounts IDs, validating integrity bounds constraints.
*   **Cascading deletes integration**: Configure sqlite cascade behaviors to clean up linked evidence files and timeline events on case deletion.
*   **REST API controllers**: Exposes endpoints under `/api/v1/cases` prefix for creating, listing, detail lookups, status transitions, user assignments, and deletions.

---

## 🚀 Version v1.0.0-beta.1 (Epic 2 Completed — AI Detection Engine Beta Release)
This milestone marks the formal completion of the AI Detection Engine (Epic 2). The system incorporates 15 fully integrated sub-phases: visual/acoustic fingerprinting, template logo identification, OCR word mappings, container metadata comparison, normalized scoring confidence levels, duplicate Jaccard clusters compiles, chronological timelines builders, immediate locks worker queues, and database WAL optimizations.

---

## 🚀 Version v1.0.0-alpha.23 (Performance Optimization)
*   **Centralized CPU metrics cache**: Integrates bounded dHash lookup dictionary `HAMMING_CACHE` caching math distances to speed visual matches.
*   **Pre-loaded Watermarks Template Cache**: Prevents repeated disk traversals and file system searches inside frame scanning loops.
*   **SQLite WAL High-throughput Write mode**: Restructures transactions to run WAL journal modes and normal sync bounds.
*   **Benchmarking reports compiler**: Measures execution latencies under concurrent ThreadPool stress environments.

---

## 🚀 Version v1.0.0-alpha.22 (Background Queue)
*   **Asynchronous Processing Daemon**: Workers query and process slow AI pipeline jobs out of the HTTP thread.
*   **Immediate Concurrency Locking**: Employs atomic SQLite `BEGIN IMMEDIATE` transactions to prevent duplicate processing operations.
*   **Failed retries limiter**: Automatically retries failed runs up to 3 times before setting a final `Failed` state.
*   **Progress Tracking Milestones**: Refreshes execution status milestones as each pipeline sub-module finishes.
*   **REST API Interfaces**: Exposes endpoints `/queue/jobs`, `/queue/jobs/{id}/retry`, and `/queue/status` for monitoring and recovery.

---

## 🚀 Version v1.0.0-alpha.20 (Timeline Builder)
*   **Central chronological events log**: Service compiles unified timeline records sorting events from all 10 engine components chronologically.
*   **Normalizations mapping**: Standardizes event properties mapping case coordinates, confidence metrics, descriptive text blocks, and timestamp offsets.
*   **Query filtering criteria**: Queries filter elements by module lists, start/end range offsets, and minimum confidence scores.
*   **REST API interfaces**: Exposes endpoints `/cases/{case_id}/timeline` and `/cases/{case_id}/timeline/events` for retrieval and manual event registrations.

---

## 🚀 Version v1.0.0-alpha.18 (Evidence Generation)
*   **Centralized evidence packaging service**: Central shared class `EvidenceGenerationService` aggregating all findings (Video, Image, Audio, OCR, Logos, Metadata, Similarity, Confidence, Duplicates).
*   **Tamper-evident checksum signatures**: Generates secure SHA-256 integrity hash verification stamps over serialized JSON blocks.
*   **Export structures**: Supports downloading JSON packages, and generates binary ZIP collections compressing enqueued logs and screenshots.
*   **REST API interfaces**: Exposes endpoints `/evidence/packages/generate`, `/evidence/packages/{id}`, `/evidence/packages/{id}/export/json`, and `/evidence/packages/{id}/export/zip`.

---

## 🚀 Version v1.0.0-alpha.16 (Duplicate Detection)
*   **Central reusable service**: Implements `DuplicateDetectionService` running comparative exact checksum (SHA-256) matches and near-duplicate (video/image/audio) checks against the entire ingested asset corpus.
*   **Clustering groups compiler**: Groups duplicate elements into hierarchical duplicate clusters anchoring a master representative anchor.
*   **Configurable similarity bounds**: Pulls duplicate classification thresholds from global constants.
*   **REST API interfaces**: Exposes endpoints `/duplicates/groups`, `/duplicates/groups/{id}`, and `/duplicates/scan` for list retrievals, details, and manual scanning triggers.

---

## 🚀 Version v1.0.0-alpha.14 (Confidence Scoring)
*   **Centralized scoring service**: Implements `ConfidenceScoringService` to evaluate match reliability across multiple modalities.
*   **Weights redistribution system**: Proportionally redistributes active weights to sum up to `1.0` if any parameters (e.g. audio stream or OCR words) are absent.
*   **Boundaries level classifications**: Maps confidence percentages to discrete classifications (`Low`, `Medium`, `High`).
*   **Narrative updates**: Serializes natural language scoring descriptions and stores enqueued results in `confidence_score` and `confidence_level` columns inside the `evidence` table.

---

## 🚀 Version v1.0.0-alpha.12 (Similarity Engine)
*   **Central fusion service**: Fuses similarity outputs from 6 modalities (Video, Image, Audio, OCR, Logos, Metadata) to calculate a unified matching verdict.
*   **Weighted linear configuration**: Consumes scoring weight matrices from global variables to facilitate parameter tuning without altering backend architectures.
*   **Temporal alignment agreement**: Awards a $+10\%$ correlation bonus if visual and audio peaks match at matching offsets, and flags a $-15\%$ penalty for temporal skew offsets (delta $> 5\text{s}$).
*   **Match explanation and timeline builder**: Compiles natural language match narratives and chronologically outputs verified timeline offsets lists.
