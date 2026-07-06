# Changelog & Checkpoint Releases

This log tracks release checkpoints of the Copyright Center.

---

## [v1.0.0-beta.11] — 2026-07-05
### Epic 4: Report Generator — Phase 4.1: DMCA Draft Notice Templates

### 1. Completed Features
*   **Notice templates configuration**: Expanded backend compiler to support five customized legal templates (Standard DMCA, YouTube Notice, TikTok IP Report, Meta Rights Complaint, Cease-and-Desist Letter).
*   **Conformed drawing signature canvas**: Integrated a mouse and touch-sensitive canvas pad enabling drawing digital signature marks.
*   **PDF Exporter engine**: Renders print-ready compliant PDF notices incorporating Case details, original references, side-by-side evidence images, and drawn electronic signatures.
*   **DOCX Exporter engine**: Exports Microsoft Word formats saving files to downloads with integrated tables and media formatting.

### 2. Test Results Summary
*   **Templates compilation**: Passed (verified metadata insertions for YouTube template type).
*   **PDF Exporter content**: Passed (verified valid content type and non-zero bytes output).
*   **DOCX Exporter content**: Passed (verified Microsoft Word binary formats generation).

---

## [v1.0.0-beta.10] — 2026-07-04
### Epic 3: Case & Evidence Management — Phase 3.5: Audit Log Viewer & Permission Model Access

### 1. Completed Features
*   **Paginated Audit Trail Reader**: Exposes paginated endpoints for system logs access, locked strictly to Admin roles.
*   **Role permissions checks**: Provides dynamic lookup maps (`/roles/me`) for active sessions permissions verifications.
*   **Append-only system integrity**: Restricts database routes to block modifying or deleting historical audit log entries.
*   **REST API controllers**: Exposes endpoints under `/api/v1/auth` prefix for user role details checks and system audit retrievals.

---

## [v1.0.0-beta.9] — 2026-07-04
### Epic 3: Case & Evidence Management — Phase 3.4: Case Archival & Export Package

### 1. Completed Features
*   **Case ZIP compiler downloads**: Bundles metadata, notes annotations, timelines, and physical attachments inside zipped streams.
*   **Database Archival transfers**: Moves closed case folders records to dedicated historical database tables `archived_cases`.
*   **Disk cleanup sweep logic**: Cleans physical disk files copies of attachments on case folder archival.
*   **REST API controllers**: Exposes endpoints under `/api/v1/cases` prefix for downloading ZIP packages and archiving folders.

---

## [v1.0.0-beta.7] — 2026-07-04
### Epic 3: Case & Evidence Management — Phase 3.3: Case Search & Annotation Logs

### 1. Completed Features
*   **Fuzzy metadata search engines**: Parameterized fuzzy matching checks case title, description, or tags fields avoiding SQL injections.
*   **Input HTML tag filters**: Auto-sanitizes annotation text inputs to prevent XSS script executions.
*   **Chronological notes listing**: Retrieves chronological notes mapping badge author usernames directly.
*   **REST API controllers**: Exposes endpoints under `/api/v1/cases` prefix for search queries, annotations logging, and listing notes.

---

## [v1.0.0-beta.5] — 2026-07-04
### Epic 3: Case & Evidence Management — Phase 3.2: Evidence Repository

### 1. Completed Features
*   **Allowed format constraints**: Restricts binary document uploads to secure formats lists (`pdf`, `png`, `jpg`, `jpeg`, `zip`) preventing script executions.
*   **Path traversal sandboxing**: Restricts target file writes to exist strictly within the attachments storage subdirectories.
*   **Cascade and manual cleanups**: Integrates database cascade removal and physical disk files cleanup routines on attachments deletes.
*   **REST API controllers**: Exposes endpoints under `/api/v1/evidence` prefix for uploading, listing, downloading, and deleting files.

---

## [v1.0.0-beta.3] — 2026-07-04
### Epic 3: Case & Evidence Management — Phase 3.1: Case Management

### 1. Completed Features
*   **Workflow State transitions**: Exposes status workflows (Active, Resolved, Closed, Suspended). Only Admins/Editors can edit cases details and link files.
*   **Decoupled user assignments**: Links owner and assignee references to user accounts IDs, validating integrity bounds constraints.
*   **Cascading deletes integration**: Configure sqlite cascade behaviors to clean up linked evidence files and timeline events on case deletion.
*   **REST API controllers**: Exposes endpoints under `/api/v1/cases` prefix for creating, listing, detail lookups, status transitions, user assignments, and deletions.

---

## [v1.0.0-beta.1] — 2026-07-04
### Epic 2 Completed — AI Detection Engine Beta Release

This milestone marks the formal completion of the AI Detection Engine (Epic 2). The system incorporates 15 fully integrated sub-phases: visual/acoustic fingerprinting, template logo identification, OCR word mappings, container metadata comparison, normalized scoring confidence levels, duplicate Jaccard clusters compiles, chronological timelines builders, immediate locks worker queues, and database WAL optimizations.

---

## [v1.0.0-alpha.23] — 2026-07-04
### Epic 2: AI Detection Engine — Sub-phase 2.15: Performance Optimization

### 1. Completed Features
*   **Centralized CPU metrics cache**: Integrates bounded dHash lookup dictionary `HAMMING_CACHE` caching math distances to speed visual matches.
*   **Pre-loaded Watermarks Template Cache**: Prevents repeated disk traversals and file system searches inside frame scanning loops.
*   **SQLite WAL High-throughput Write mode**: Restructures transactions to run WAL journal modes and normal sync bounds.
*   **Benchmarking reports compiler**: Measures execution latencies under concurrent ThreadPool stress environments.

---

## [v1.0.0-alpha.22] — 2026-07-04
### Epic 2: AI Detection Engine — Sub-phase 2.14: Background Queue

### 1. Completed Features
*   **Asynchronous Processing Daemon**: Workers query and process slow AI pipeline jobs out of the HTTP thread.
*   **Immediate Concurrency Locking**: Employs atomic SQLite `BEGIN IMMEDIATE` transactions to prevent duplicate processing operations.
*   **Failed retries limiter**: Automatically retries failed runs up to 3 times before setting a final `Failed` state.
*   **Progress Tracking Milestones**: Refreshes execution status milestones as each pipeline sub-module finishes.
*   **REST API Interfaces**: Exposes endpoints `/queue/jobs`, `/queue/jobs/{id}/retry`, and `/queue/status` for monitoring and recovery.

---

## [v1.0.0-alpha.20] — 2026-07-04
### Epic 2: AI Detection Engine — Sub-phase 2.13: Timeline Builder

### 1. Completed Features
*   **Central chronological events log**: Service compiles unified timeline records sorting events from all 10 engine components chronologically.
*   **Normalizations mapping**: Standardizes event properties mapping case coordinates, confidence metrics, descriptive text blocks, and timestamp offsets.
*   **Query filtering criteria**: Queries filter elements by module lists, start/end range offsets, and minimum confidence scores.
*   **REST API interfaces**: Exposes endpoints `/cases/{case_id}/timeline` and `/cases/{case_id}/timeline/events` for retrieval and manual event registrations.

---

## [v1.0.0-alpha.18] — 2026-07-04
### Epic 2: AI Detection Engine — Sub-phase 2.12: Evidence Generation

### 1. Completed Features
*   **Centralized evidence packaging service**: Central shared class `EvidenceGenerationService` aggregating all findings (Video, Image, Audio, OCR, Logos, Metadata, Similarity, Confidence, Duplicates).
*   **Tamper-evident checksum signatures**: Generates secure SHA-256 integrity hash verification stamps over serialized JSON blocks.
*   **Export structures**: Supports downloading JSON packages, and generates binary ZIP collections compressing enqueued logs and screenshots.
*   **REST API interfaces**: Exposes endpoints `/evidence/packages/generate`, `/evidence/packages/{id}`, `/evidence/packages/{id}/export/json`, and `/evidence/packages/{id}/export/zip`.

---

## [v1.0.0-alpha.16] — 2026-07-04
### Epic 2: AI Detection Engine — Sub-phase 2.11: Duplicate Detection

### 1. Completed Features
*   **Central reusable service**: Implements `DuplicateDetectionService` running comparative exact checksum (SHA-256) matches and near-duplicate (video/image/audio) checks against the entire ingested asset corpus.
*   **Clustering groups compiler**: Groups duplicate elements into hierarchical duplicate clusters anchoring a master representative anchor.
*   **Configurable similarity bounds**: Pulls duplicate classification thresholds from global constants.
*   **REST API interfaces**: Exposes endpoints `/duplicates/groups`, `/duplicates/groups/{id}`, and `/duplicates/scan` for list retrievals, details, and manual scanning triggers.

---

## [v1.0.0-alpha.14] — 2026-07-04
### Epic 2: AI Detection Engine — Sub-phase 2.10: Confidence Scoring

### 1. Completed Features
*   **Centralized scoring service**: Implements `ConfidenceScoringService` to evaluate match reliability across multiple modalities.
*   **Weights redistribution system**: Proportionally redistributes active weights to sum up to `1.0` if any parameters (e.g. audio stream or OCR words) are absent.
*   **Boundaries level classifications**: Maps confidence percentages to discrete classifications (`Low`, `Medium`, `High`).
*   **Narrative updates**: Serializes natural language scoring descriptions and stores enqueued results in `confidence_score` and `confidence_level` columns inside the `evidence` table.

---

## [v1.0.0-alpha.12] — 2026-07-04
### Epic 2: AI Detection Engine — Sub-phase 2.9: Similarity Engine

### 1. Completed Features
*   **Central fusion service**: Fuses similarity outputs from 6 modalities (Video, Image, Audio, OCR, Logos, Metadata) to calculate a unified matching verdict.
*   **Weighted linear configuration**: Consumes scoring weight matrices from global variables to facilitate parameter tuning without altering backend architectures.
*   **Temporal alignment agreement**: Awards a $+10\%$ correlation bonus if visual and audio peaks match at matching offsets, and flags a $-15\%$ penalty for temporal skew offsets (delta $> 5\text{s}$).
*   **Match explanation and timeline builder**: Compiles natural language match narratives and chronologically outputs verified timeline offsets lists.

---

## [v1.0.0-alpha.10] — 2026-07-04
### Epic 2: AI Detection Engine — Sub-phase 2.8: Metadata Analysis

### 1. Completed Features
*   **Decoupled extractor dispatcher**: OOP interface class `BaseMetadataExtractor` allowing modular addition of format extractors.
*   **Video/Image/Audio properties parsing**: Leverages OpenCV, PIL, and native `wave` channels to retrieve codecs, sizes, resolution tuples, bitrates, sample rates, EXIF and durations.
*   **Hash integrity validators**: Computes SHA-256 and MD5 checksum signatures.
*   **Comparative analysis engine**: Evaluates aspect ratios (within $\pm 0.01$ margin) and durations (within $\pm 2.0\text{ seconds}$ bounds) to log modified and missing property fields.

---

## [v1.0.0-alpha.9] — 2026-07-04
### Epic 2: AI Detection Engine — Sub-phase 2.7: Logo Detection

### 1. Completed Features
*   **OOP modular interface**: Abstract base class `BaseLogoDetector` to decouple templates search models.
*   **Multi-Logo template matcher**: `TemplateMatchingLogoDetector` mapping concurrent platform watermark overlaps.
*   **Structured coordinates**: Logs bounding boxes, confidence values, and offsets JSON objects under `logo_metadata_json` columns.
*   **Non-duplicative frames reuse**: Feeds decoded frame arrays directly to detectors to preserve CPU seeking latency.

---

## [v1.0.0-alpha.7] — 2026-07-04
### Epic 2: AI Detection Engine — Sub-phase 2.6: OCR Text Recognition

### 1. Completed Features
*   **OTSU threshold binarization**: Pre-processes evidence frames using Otsu binarization to optimize text foreground separation.
*   **Gaussian denoising**: Eliminates pixel noise via $3\times3$ Gaussian blur filters.
*   **Tesseract LSTM wrapper**: Core pytesseract bindings extracting English and Khmer (`eng+khm`) text overlays.
*   **Confidence thresholding**: Ignores OCR words returning confidence values below $60\%$.
*   **API endpoints**: Implements manual trigger `/ocr/scan` and getter `/ocr/{id}` endpoints.

---

## [v1.0.0-alpha.6] — 2026-07-04
### Epic 2: AI Detection Engine — Sub-phase 2.5: Frame Extraction

### 1. Completed Features
*   **Timestamp seeking**: OpenCV millisecond seeks (`CAP_PROP_POS_MSEC`) to retrieve frame decodings.
*   **Dimension scaling**: Aspect-ratio preserving height scaling (360px height target) to optimize response transfer payloads.
*   **Scrubbing REST API**: Exposes `GET /api/v1/originals/{id}/frame` returning streaming JPEG binary response payloads.
*   **Bounds verification checks**: Validates seek timestamps against actual file durations.

---

## [v1.0.0-alpha.5] — 2026-07-04
### Epic 2: AI Detection Engine — Sub-phase 2.4: Audio Fingerprinting

### 1. Completed Features
*   **Acoustic Demuxing**: Video audio demuxer extracting mono PCM 16-bit 8000Hz WAV structures.
*   **Spectrogram Peak FFT**: Discrete Fourier Transforms (FFT) mapping dominant coordinate frequency peaks (128ms intervals).
*   **Relative Delta Pitch Tracker**: Tracks relative frequency shifts between coordinates to survive pitch distortions.
*   **Jaccard Correlation Similarity**: Acoustic matching check using coordinates set intersection overlays.

---

## [v1.0.0-alpha.4] — 2026-07-04
### Epic 2: AI Detection Engine — Sub-phase 2.3: Image Fingerprinting

### 1. Completed Features
*   **Image dHash Extraction**: Custom difference hashing generating a 16-character hexadecimal signature string for static images.
*   **CLAHE Equalization**: Image contrast levels normalization to withstand brightness fluctuations.
*   **Noise Filtering**: Gaussian blur filters to remove pixel noise.
*   **Platform Watermark Crops**: Bounding crop ($5\%$ off outer borders) to eliminate platform watermarks and layout paddings.
