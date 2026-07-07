# Database Schema Reference - TSN Copyright Defender

The platform utilizes a local SQLite database engine stored at `storage/database.db` with Write-Ahead Logging (WAL) enabled.

---

## 1. Relational Schema & Tables

### A. Users & Sessions
- **`users`**: Registers user details.
  - `role` CHECK constraint: `role IN ('Admin', 'Editor', 'Reviewer', 'Guest')`.
- **`sessions`**: Active tokens validation.
  - Cascade delete on `user_id`.

### B. Cases & Evidence Ledger
- **`cases`**: Represents a case folder.
  - Check constraint: `length(title) > 0`.
  - Priority CHECK: `IN ('Critical', 'High', 'Medium', 'Low')`.
  - Status CHECK: `IN ('Draft', 'Investigating', 'Scanning', 'Evidence Collected', 'Verified', 'DMCA Draft', 'DMCA Sent', 'Resolved', 'Archived', 'Active', 'Closed', 'Suspended')`.
- **`evidence`**: formal matched copyright infringement logs.
  - Platform CHECK: `IN ('YouTube', 'TikTok', 'Facebook', 'Instagram', 'Other')`.
  - Status CHECK: `IN ('Detected', 'Verified', 'DMCA Drafted', 'DMCA Filed', 'Resolved')`.
- **`case_evidence`**: Junction bridge table mapping multiple cases to evidence rows.
- **`evidence_attachments`**: PDF proofs and file documents attached to evidence.
- **`assets`**: Reference files uploaded to the Asset Library.
  - `asset_type` CHECK: `IN ('Video', 'Image', 'Audio', 'Document', 'Logo', 'Trademark')`.
  - `status` CHECK: `IN ('Active', 'Archived', 'Deleted')`.
  - `fingerprint_status` CHECK: `IN ('Pending', 'Processing', 'Completed', 'Failed', 'N/A')`.

### C. Scan Queue & Results
- **`scan_jobs`**: Asynchronous scan tasks.
  - Platform CHECK: `IN ('YouTube', 'TikTok', 'Instagram', 'Facebook Post', 'Facebook Ad Library', 'Website', 'Other')`.
  - Status CHECK: `IN ('Pending', 'Running', 'Completed', 'Failed', 'Cancelled')`.
- **`scan_results`**: Extracted metadata and thumbnail screenshot details.
- **`background_jobs`**: Legacy queue engine tracking files hash extraction.
  - Job types CHECK: `IN ('fingerprint_original', 'scan_link', 'fingerprint_video', 'fingerprint_audio')`.
  - Status CHECK: `IN ('Queued', 'Processing', 'Completed', 'Failed', 'Cancelled')`.

---

## 2. Core Index Configurations

```sql
-- Security & Audits
CREATE INDEX idx_sessions_token ON sessions(token);
CREATE INDEX idx_audit_user ON audit_logs(user_id);

-- Performance Tuning
CREATE INDEX idx_assets_hash ON assets(sha256_hash);
CREATE INDEX idx_evidence_hash ON evidence(sha256_hash);
CREATE INDEX idx_case_evidence_junction ON case_evidence(case_id, evidence_id);
CREATE INDEX idx_scan_results_job_id ON scan_results(job_id);
CREATE INDEX idx_scan_jobs_status ON scan_jobs(status);
```
