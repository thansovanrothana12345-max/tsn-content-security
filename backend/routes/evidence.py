from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
import json
from backend.database import get_db_connection
from backend.routes.auth import require_role

router = APIRouter(prefix="/api/v1/evidence", tags=["Evidence"])

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVIDENCE_DIR = os.path.join(PROJECT_ROOT, "storage", "evidence")

class ScanRequest(BaseModel):
    case_id: int
    url: str

class StatusUpdateRequest(BaseModel):
    status: str

# 1. List evidence for a case
@router.get("/{case_id}")
def list_evidence(
    case_id: int,
    q: str = None,
    file_type: str = None,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM evidence WHERE case_id = ? ORDER BY similarity_score DESC, created_at DESC", 
            (case_id,)
        )
        rows = cursor.fetchall()
        results = [dict(row) for row in rows]
        
        if q:
            q_lower = q.lower()
            results = [r for r in results if q_lower in (r.get("title") or "").lower() or q_lower in (r.get("uploader") or "").lower() or q_lower in (r.get("url") or "").lower()]
        if file_type:
            file_type_lower = file_type.lower()
            if file_type_lower == "image":
                results = [r for r in results if (r.get("file_type") or "").startswith("image/")]
            elif file_type_lower == "document":
                results = [r for r in results if (r.get("file_type") or "").startswith("application/") or (r.get("file_type") or "").startswith("text/") or r.get("file_type") == "document"]
                
        return results
    finally:
        conn.close()

# 2. Queue background URL scan job
@router.post("/scan", status_code=202)
def scan_evidence(request: ScanRequest, user: dict = Depends(require_role(["Admin", "Editor", "Reviewer"]))):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify case exists
    cursor.execute("SELECT id FROM cases WHERE id = ?", (request.case_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(
            status_code=404, 
            detail={"error": "NOT_FOUND", "message": "The requested case folder does not exist."}
        )
        
    # Queue background scan job
    job_payload = json.dumps({"url": request.url, "user_id": user["id"]})
    cursor.execute("""
        INSERT INTO background_jobs (case_id, job_type, status, payload_json)
        VALUES (?, 'scan_link', 'Queued', ?)
    """, (request.case_id, job_payload))
    job_id = cursor.lastrowid
    
    # Log audit entry
    details = json.dumps({"url": request.url, "job_id": job_id})
    cursor.execute("""
        INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
        VALUES (?, 'ENQUEUE_SCAN', 'case', ?, ?)
    """, (user["id"], request.case_id, details))
    
    conn.commit()
    conn.close()
    
    return {
        "job_id": job_id,
        "case_id": request.case_id,
        "status": "Queued",
        "message": "Scan job successfully queued in background worker."
    }

# 3. Update Evidence Status
@router.put("/{evidence_id}/status")
def update_evidence_status(
    evidence_id: int, 
    request: StatusUpdateRequest, 
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer"]))
):
    if request.status not in ['Detected', 'Verified', 'DMCA Drafted', 'DMCA Filed', 'Resolved']:
        raise HTTPException(
            status_code=400, 
            detail={"error": "BAD_REQUEST", "message": "Invalid evidence status."}
        )
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,))
    existing = cursor.fetchone()
    if not existing:
        conn.close()
        raise HTTPException(
            status_code=404, 
            detail={"error": "NOT_FOUND", "message": "Evidence not found."}
        )
        
    cursor.execute("UPDATE evidence SET status = ? WHERE id = ?", (request.status, evidence_id))
    
    # Audit log
    details = json.dumps({"old_status": existing["status"], "new_status": request.status})
    cursor.execute("""
        INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
        VALUES (?, 'UPDATE_EVIDENCE_STATUS', 'evidence', ?, ?)
    """, (user["id"], evidence_id, details))
    
    conn.commit()
    
    cursor.execute("SELECT * FROM evidence WHERE id = ?", (evidence_id,))
    updated = cursor.fetchone()
    conn.close()
    return dict(updated)

# 4. Delete Evidence
@router.delete("/{evidence_id}")
def delete_evidence(evidence_id: int, user: dict = Depends(require_role(["Admin"]))):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT case_id, title, screenshot_path FROM evidence WHERE id = ?", (evidence_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(
            status_code=404, 
            detail={"error": "NOT_FOUND", "message": "Evidence not found."}
        )
        
    # Delete from DB
    cursor.execute("DELETE FROM evidence WHERE id = ?", (evidence_id,))
    
    # Clean up duplicate groups where this evidence was representative or member
    evidence_uuid_str = str(evidence_id)
    cursor.execute("DELETE FROM duplicate_groups WHERE representative_file_uuid = ? AND representative_file_type = 'evidence';", (evidence_uuid_str,))
    cursor.execute("DELETE FROM duplicate_group_members WHERE member_file_uuid = ? AND member_file_type = 'evidence';", (evidence_uuid_str,))
    
    # Audit log
    details = json.dumps({"title": row["title"]})
    cursor.execute("""
        INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
        VALUES (?, 'DELETE_EVIDENCE', 'evidence', ?, ?)
    """, (user["id"], evidence_id, details))
    
    conn.commit()
    conn.close()
    
    # Delete local thumbnail file if it exists
    screenshot_path = row["screenshot_path"]
    if screenshot_path and screenshot_path.startswith("/storage/evidence/"):
        filename = os.path.basename(screenshot_path)
        full_path = os.path.join(EVIDENCE_DIR, filename)
        if os.path.exists(full_path):
            try:
                os.remove(full_path)
            except Exception as e:
                print(f"Error removing screenshot file: {e}")
                
    return {"message": f"Evidence {evidence_id} deleted successfully."}

# 5. Get OCR Text Recognition results
@router.get("/ocr/{evidence_id}")
def get_evidence_ocr(
    evidence_id: int, 
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves OCR extracted text and word coordinate metadata from evidence."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, case_id, ocr_text, ocr_metadata_json FROM evidence WHERE id = ?", (evidence_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(
            status_code=404, 
            detail={"error": "NOT_FOUND", "message": "Evidence record not found."}
        )
        
    metadata = []
    if row["ocr_metadata_json"]:
         try:
              metadata = json.loads(row["ocr_metadata_json"])
         except Exception:
              pass
              
    return {
         "id": row["id"],
         "case_id": row["case_id"],
         "ocr_text": row["ocr_text"] or "",
         "ocr_metadata": metadata
    }

class OCRScanRequest(BaseModel):
    evidence_id: int

# 6. Manually execute OCR scan on screenshot
@router.post("/ocr/scan")
def trigger_evidence_ocr_scan(
    request: OCRScanRequest, 
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer"]))
):
    """Triggers OCR text recognition extraction on evidence screenshot file."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, case_id, screenshot_path FROM evidence WHERE id = ?", (request.evidence_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(
            status_code=404, 
            detail={"error": "NOT_FOUND", "message": "Evidence record not found."}
        )
        
    screenshot_path = row["screenshot_path"]
    if not screenshot_path:
        conn.close()
        raise HTTPException(
            status_code=400, 
            detail={"error": "BAD_REQUEST", "message": "Evidence does not have a screenshot proof."}
        )
        
    filename = os.path.basename(screenshot_path)
    physical_path = os.path.join(EVIDENCE_DIR, filename)
    
    if not os.path.exists(physical_path):
        conn.close()
        raise HTTPException(
            status_code=404, 
            detail={"error": "NOT_FOUND", "message": f"Physical screenshot file not found: {filename}"}
        )
        
    from backend.fingerprint import extract_ocr_text
    
    ocr_results = extract_ocr_text(physical_path)
    
    cursor.execute("""
        UPDATE evidence 
        SET ocr_text = ?, ocr_metadata_json = ? 
        WHERE id = ?
    """, (ocr_results["ocr_text"], json.dumps(ocr_results["ocr_metadata"]), request.evidence_id))
    
    details = json.dumps({"triggered_by": user["username"]})
    cursor.execute("""
        INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
        VALUES (?, 'OCR_SCAN_EXECUTED', 'evidence', ?, ?)
    """, (user["id"], request.evidence_id, details))
    
    conn.commit()
    conn.close()
    
    return {
         "message": "OCR text extraction finished successfully.",
         "ocr_text": ocr_results["ocr_text"],
         "ocr_metadata": ocr_results["ocr_metadata"]
    }

# 7. Duplicate Detection Endpoints (Sub-phase 2.11)
@router.get("/duplicates/groups")
def get_duplicate_groups(
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves all duplicate cluster groups."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, representative_file_uuid, representative_file_type, created_at FROM duplicate_groups;")
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/duplicates/groups/{group_id}")
def get_duplicate_group_details(
    group_id: int,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves details of a specific duplicate group and its members."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, representative_file_uuid, representative_file_type, created_at FROM duplicate_groups WHERE id = ?;", (group_id,))
    group = cursor.fetchone()
    if not group:
         conn.close()
         raise HTTPException(status_code=404, detail="Duplicate group not found.")
         
    cursor.execute("""
         SELECT id, member_file_uuid, member_file_type, similarity_score, is_exact, created_at 
         FROM duplicate_group_members 
         WHERE group_id = ?;
    """, (group_id,))
    members = cursor.fetchall()
    conn.close()
    
    return {
         "group": dict(group),
         "members": [dict(m) for m in members]
    }

class DuplicateScanRequest(BaseModel):
    target_uuid: str
    target_type: str # 'original' or 'evidence'

@router.post("/duplicates/scan")
def run_duplicate_scan(
    request: DuplicateScanRequest,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Triggers duplicate scan for a specific ingested file against the entire corpus."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if request.target_type == "original":
         cursor.execute("SELECT filename, filesize, duration, fingerprint_json, metadata_analysis_json FROM originals WHERE file_uuid = ?;", (request.target_uuid,))
         target = cursor.fetchone()
         if not target:
              conn.close()
              raise HTTPException(status_code=404, detail="Target original file not found.")
         fp_data = {
              "category": "video" if target["duration"] > 0 else "image",
              "file_properties": {
                   "filesize": target["filesize"],
                   "sha256": request.target_uuid
              },
              "fingerprint": json.loads(target["fingerprint_json"]) if target["fingerprint_json"] else []
         }
         try:
              if target["metadata_analysis_json"]:
                   fp_data["metadata"] = json.loads(target["metadata_analysis_json"])
         except Exception:
              pass
    else:
         try:
              evidence_id = int(request.target_uuid)
         except ValueError:
              conn.close()
              raise HTTPException(status_code=400, detail="Invalid target ID for evidence category.")
              
         cursor.execute("SELECT id, case_id, platform, similarity_score, ocr_text, logo_metadata_json FROM evidence WHERE id = ?;", (evidence_id,))
         target = cursor.fetchone()
         if not target:
              conn.close()
              raise HTTPException(status_code=404, detail="Target evidence file not found.")
         fp_data = {
              "category": "video",
              "file_properties": {"sha256": f"evidence-sha-{evidence_id}"},
              "fingerprint": []
         }
         
    cursor.execute("SELECT id, file_uuid, filename, filesize, duration, fingerprint_json, metadata_analysis_json FROM originals;")
    corpus_rows = cursor.fetchall()
    corpus_assets = []
    for row in corpus_rows:
         if row["file_uuid"] == request.target_uuid:
              continue
         fp_json = json.loads(row["fingerprint_json"]) if row["fingerprint_json"] else []
         meta_dict = {}
         try:
              if row["metadata_analysis_json"]:
                   meta_dict = json.loads(row["metadata_analysis_json"])
         except Exception:
              pass
              
         corpus_assets.append({
              "uuid": row["file_uuid"],
              "type": "original",
              "category": "video" if row["duration"] > 0 else "image",
              "fingerprint_data": {
                   "category": "video" if row["duration"] > 0 else "image",
                   "file_properties": {"filesize": row["filesize"], "sha256": row["file_uuid"]},
                   "fingerprint": fp_json,
                   "metadata": meta_dict
              }
         })
         
    from backend.fingerprint import DuplicateDetectionService
    scanner = DuplicateDetectionService()
    duplicates = scanner.scan_for_duplicates(conn, request.target_uuid, request.target_type, fp_data, corpus_assets)
    
    conn.close()
    return {
         "target_uuid": request.target_uuid,
         "duplicates_found": len(duplicates),
         "duplicates": duplicates
    }

# 8. Evidence Package Endpoints (Sub-phase 2.12)
class EvidencePackageGenerateRequest(BaseModel):
    evidence_id: int

@router.post("/packages/generate")
def generate_evidence_package(
    request: EvidencePackageGenerateRequest,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Compiles all findings for an evidence ID and registers a structured package."""
    conn = get_db_connection()
    try:
         from backend.fingerprint import EvidenceGenerationService
         service = EvidenceGenerationService()
         package = service.generate_package(conn, request.evidence_id)
         return package
    except ValueError as e:
         raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Evidence packaging failed: {e}")
    finally:
         conn.close()

@router.get("/packages/{package_id}")
def get_evidence_package(
    package_id: int,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves detailed parameters of a compiled evidence package."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, evidence_id, case_id, evidence_hash, package_json FROM evidence_packages WHERE id = ?;", (package_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
         raise HTTPException(status_code=404, detail="Evidence package not found.")
         
    return json.loads(row["package_json"])

@router.get("/packages/{package_id}/export/json")
def export_evidence_package_json(
    package_id: int,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Downloads the evidence package as a JSON file."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, package_json FROM evidence_packages WHERE id = ?;", (package_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
         raise HTTPException(status_code=404, detail="Evidence package not found.")
         
    from fastapi.responses import Response
    package_data = json.loads(row["package_json"])
    return Response(
         content=json.dumps(package_data, indent=4),
         media_type="application/json",
         headers={"Content-Disposition": f"attachment; filename=evidence_package_{package_id}.json"}
    )

@router.get("/packages/{package_id}/export/zip")
def export_evidence_package_zip(
    package_id: int,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Downloads the evidence package and physical screenshots compiled as a ZIP package file."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, package_json FROM evidence_packages WHERE id = ?;", (package_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
         raise HTTPException(status_code=404, detail="Evidence package not found.")
         
    from backend.fingerprint import EvidenceGenerationService
    from fastapi.responses import StreamingResponse
    import io
    
    package = json.loads(row["package_json"])
    service = EvidenceGenerationService()
    zip_bytes = service.export_zip(package, EVIDENCE_DIR)
    
    return StreamingResponse(
         io.BytesIO(zip_bytes),
         media_type="application/zip",
         headers={"Content-Disposition": f"attachment; filename=evidence_package_{package_id}.zip"}
    )

# 9. Timeline Builder Endpoints (Sub-phase 2.13)
class TimelineEventCreateRequest(BaseModel):
    evidence_id: int | None = None
    module_name: str
    event_type: str
    timestamp: float
    confidence: float
    description: str

@router.get("/cases/{case_id}/timeline")
def get_case_timeline(
    case_id: int,
    modules: str = None,
    event_types: str = None,
    start_time: float = None,
    end_time: float = None,
    min_confidence: float = None,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves chronological timeline events for a given case, applying custom query filters."""
    conn = get_db_connection()
    filters = {}
    if modules:
         filters["modules"] = [m.strip() for m in modules.split(",") if m.strip()]
    if event_types:
         filters["event_types"] = [et.strip() for et in event_types.split(",") if et.strip()]
    if start_time is not None:
         filters["start_time"] = start_time
    if end_time is not None:
         filters["end_time"] = end_time
    if min_confidence is not None:
         filters["min_confidence"] = min_confidence
         
    from backend.fingerprint import TimelineBuilderService
    service = TimelineBuilderService()
    events = service.build_timeline(conn, case_id, filters)
    conn.close()
    return events

@router.post("/cases/{case_id}/timeline/events")
def add_case_timeline_event(
    case_id: int,
    request: TimelineEventCreateRequest,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Manually registers a new timeline event for auditing remarks or case tracking."""
    conn = get_db_connection()
    from backend.fingerprint import TimelineBuilderService
    service = TimelineBuilderService()
    event_id = service.register_event(
         conn,
         case_id=case_id,
         evidence_id=request.evidence_id,
         module_name=request.module_name,
         event_type=request.event_type,
         timestamp=request.timestamp,
         confidence=request.confidence,
         description=request.description
    )
    conn.close()
    return {"message": "Timeline event created successfully.", "event_id": event_id}

# 10. Background Queue Endpoints (Sub-phase 2.14)
class QueueJobCreateRequest(BaseModel):
    case_id: int
    evidence_id: int | None = None
    job_type: str
    payload: dict
    priority: int = 2

@router.post("/queue/jobs")
def create_queue_job(
    request: QueueJobCreateRequest,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Enqueues a new background processing job."""
    conn = get_db_connection()
    from backend.fingerprint import JobsQueueService
    service = JobsQueueService()
    job_id = service.enqueue_job(
         conn,
         case_id=request.case_id,
         evidence_id=request.evidence_id,
         job_type=request.job_type,
         payload=request.payload,
         priority=request.priority
    )
    conn.close()
    return {"message": "Background job enqueued successfully.", "job_id": job_id}

@router.get("/queue/jobs/{job_id}")
def get_queue_job_status(
    job_id: int,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves status details and execution progress of a background job."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
         SELECT id, case_id, evidence_id, job_type, status, priority, progress_percentage, retries_count, max_retries, error_traceback, created_at, updated_at, started_at, completed_at 
         FROM jobs_queue 
         WHERE id = ?;
    """, (job_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
         raise HTTPException(status_code=404, detail="Background job not found.")
         
    return dict(row)

@router.post("/queue/jobs/{job_id}/retry")
def retry_queue_job(
    job_id: int,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Manually resets a failed or stuck job back to Queued status."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, status FROM jobs_queue WHERE id = ?;", (job_id,))
    row = cursor.fetchone()
    if not row:
         conn.close()
         raise HTTPException(status_code=404, detail="Background job not found.")
         
    cursor.execute("""
         UPDATE jobs_queue 
         SET status = 'Queued', retries_count = 0, error_traceback = NULL, started_at = NULL, completed_at = NULL, progress_percentage = 0.0 
         WHERE id = ?;
    """, (job_id,))
    conn.commit()
    conn.close()
    return {"message": "Background job reset to Queued successfully."}

@router.get("/queue/status")
def get_queue_monitoring_stats(
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves real-time counts across Queued, Processing, Completed, and Failed jobs."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, COUNT(*) as cnt FROM jobs_queue GROUP BY status;")
    rows = cursor.fetchall()
    conn.close()
    
    stats = {"Queued": 0, "Processing": 0, "Completed": 0, "Failed": 0}
    for row in rows:
         stats[row["status"]] = row["cnt"]
         
    return stats

# 12. Evidence Attachments Routes (Sub-phase 3.2)
@router.post("/{evidence_id}/attachments", status_code=201)
def upload_evidence_attachment(
    evidence_id: int,
    file: UploadFile = File(...),
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Uploads binary document attachments linking to evidence records."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM evidence WHERE id = ?;", (evidence_id,))
    if not cursor.fetchone():
         conn.close()
         raise HTTPException(status_code=404, detail="Parent evidence record not found.")
         
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower().replace(".", "")
    if ext not in ["pdf", "png", "jpg", "jpeg", "zip"]:
         conn.close()
         raise HTTPException(status_code=400, detail="Forbidden file format extensions.")
         
    attachments_dir = os.path.join(PROJECT_ROOT, "storage", "attachments")
    os.makedirs(attachments_dir, exist_ok=True)
    
    safe_filename = "".join(c for c in filename if c.isalnum() or c in (".", "_", "-"))
    target_filepath = os.path.abspath(os.path.join(attachments_dir, safe_filename))
    if not target_filepath.startswith(os.path.abspath(attachments_dir)):
         conn.close()
         raise HTTPException(status_code=400, detail="Invalid path destination.")
         
    contents = file.file.read()
    filesize = len(contents)
    if filesize > 20 * 1024 * 1024:
         conn.close()
         raise HTTPException(status_code=400, detail="Payload file exceeds maximum permitted size of 20MB.")
         
    with open(target_filepath, "wb") as f:
         f.write(contents)
         
    cursor.execute("""
         INSERT INTO evidence_attachments (evidence_id, filename, filepath, filesize)
         VALUES (?, ?, ?, ?);
    """, (evidence_id, safe_filename, target_filepath, filesize))
    attachment_id = cursor.lastrowid
    
    details = json.dumps({"filename": safe_filename, "filesize": filesize})
    cursor.execute("""
         INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
         VALUES (?, 'UPLOAD_ATTACHMENT', 'attachment', ?, ?);
    """, (user["id"], attachment_id, details))
    
    conn.commit()
    conn.close()
    
    return {
         "id": attachment_id,
         "evidence_id": evidence_id,
         "filename": safe_filename,
         "filepath": target_filepath,
         "filesize": filesize
    }

@router.get("/{evidence_id}/attachments")
def list_evidence_attachments(
    evidence_id: int,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Lists all document attachments details matching evidence ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, evidence_id, filename, filepath, filesize, created_at FROM evidence_attachments WHERE evidence_id = ?;", (evidence_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

@router.get("/attachments/{attachment_id}/download")
def download_evidence_attachment(
    attachment_id: int,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Downloads binary document attachments."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT filepath, filename FROM evidence_attachments WHERE id = ?;", (attachment_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
         raise HTTPException(status_code=404, detail="Attachment file not found.")
         
    filepath = row["filepath"]
    if not os.path.exists(filepath):
         raise HTTPException(status_code=404, detail="Physical attachment file missing on server storage.")
         
    return FileResponse(filepath, filename=row["filename"], media_type="application/octet-stream")

@router.delete("/attachments/{attachment_id}")
def delete_evidence_attachment(
    attachment_id: int,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Deletes attachment from database and cleans from physical disks."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT filepath, filename, id FROM evidence_attachments WHERE id = ?;", (attachment_id,))
    row = cursor.fetchone()
    if not row:
         conn.close()
         raise HTTPException(status_code=404, detail="Attachment file not found.")
         
    cursor.execute("DELETE FROM evidence_attachments WHERE id = ?;", (attachment_id,))
    
    details = json.dumps({"filename": row["filename"]})
    cursor.execute("""
         INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
         VALUES (?, 'DELETE_ATTACHMENT', 'attachment', ?, ?);
    """, (user["id"], attachment_id, details))
    
    conn.commit()
    conn.close()
    
    if os.path.exists(row["filepath"]):
         try:
              os.remove(row["filepath"])
         except Exception:
              pass
              
    return {"message": "Attachment file deleted successfully."}


# 13. Case-based Evidence File Upload Routes
@router.post("/upload/{case_id}", status_code=201)
def upload_evidence_file(
    case_id: int,
    file: UploadFile = File(...),
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer"]))
):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM cases WHERE id = ?", (case_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Case not found.")
            
        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()
        if ext in [".exe", ".bat", ".cmd", ".sh"]:
            raise HTTPException(status_code=400, detail="Unsafe file format.")
            
        # Ensure evidence directory exists
        os.makedirs(EVIDENCE_DIR, exist_ok=True)
        
        # Generate unique filename to avoid collision
        import uuid
        unique_filename = f"{uuid.uuid4()}{ext}"
        target_path = os.path.join(EVIDENCE_DIR, unique_filename)
        
        # Save file contents
        content = file.file.read()
        file_size = len(content)
        with open(target_path, "wb") as f:
            f.write(content)
            
        # Determine platform and MIME type
        platform = "Other"
        file_type = file.content_type or "application/octet-stream"
        
        # Insert into database
        import datetime
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO evidence (case_id, platform, url, title, uploader, upload_date, status, screenshot_path, file_type, file_size)
            VALUES (?, ?, ?, ?, ?, ?, 'Detected', ?, ?, ?)
        """, (case_id, platform, f"/api/v1/evidence/file/{unique_filename}", filename, user["username"], now_str, f"/storage/evidence/{unique_filename}", file_type, file_size))
        evidence_id = cursor.lastrowid
        conn.commit()
        
        return {
            "success": True,
            "message": "Evidence uploaded successfully",
            "id": evidence_id,
            "case_id": case_id,
            "filename": filename,
            "file_type": file_type,
            "file_size": file_size,
            "url": f"/api/v1/evidence/file/{unique_filename}"
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/file/{filename}")
def retrieve_evidence_file(
    filename: str,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    # Path traversal safety check
    safe_filename = os.path.basename(filename)
    if safe_filename != filename or ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid path destination.")
        
    filepath = os.path.join(EVIDENCE_DIR, safe_filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found.")
        
    return FileResponse(filepath)


