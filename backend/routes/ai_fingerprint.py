from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List
import os
import uuid
import datetime
import json
import sqlite3
from backend.database import get_db_connection
from backend.routes.auth import require_role
from backend.ai.services.orchestrator import AIServiceOrchestrator
from backend.config import Config

router = APIRouter(prefix="/api/v2", tags=["AI Fingerprint"])

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EVIDENCE_DIR = os.path.join(PROJECT_ROOT, Config.STORAGE_DIR, "evidence")

class SimilarityCheckRequest(BaseModel):
    case_id: int
    source_id: int
    source_type: str # 'evidence' or 'original'
    target_id: int
    target_type: str # 'evidence' or 'original'
    match_types: Optional[List[str]] = ["perceptual_hash", "embedding"]

@router.post("/fingerprint/image", status_code=201)
def fingerprint_image_endpoint(
    case_id: int = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer"]))
):
    """Synchronously fingerprints an image and registers it as evidence."""
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        raise HTTPException(status_code=400, detail="Unsupported image extension format.")
        
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    unique_filename = f"{uuid.uuid4()}{ext}"
    target_path = os.path.join(EVIDENCE_DIR, unique_filename)
    
    # Save file contents
    content = file.file.read()
    file_size = len(content)
    import hashlib
    sha256_hash = hashlib.sha256(content).hexdigest()
    with open(target_path, "wb") as f:
        f.write(content)
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if case exists
        cursor.execute("SELECT id FROM cases WHERE id = ?", (case_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Case not found.")
            
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_type = file.content_type or "image/jpeg"
        
        # Insert evidence record
        cursor.execute("""
            INSERT INTO evidence (case_id, platform, url, title, uploader, upload_date, status, screenshot_path, file_type, file_size, sha256_hash)
            VALUES (?, 'Other', ?, ?, ?, ?, 'Detected', ?, ?, ?, ?)
        """, (case_id, f"/api/v1/evidence/file/{unique_filename}", filename, user["username"], now_str, f"/storage/evidence/{unique_filename}", file_type, file_size, sha256_hash))
        
        evidence_id = cursor.lastrowid
        conn.commit()
        
        # Ingest fingerprint via Orchestrator
        fp_id = AIServiceOrchestrator.ingest_fingerprint(case_id, "evidence", evidence_id, target_path)
        
        # Retrieve computed fingerprint details to return
        cursor.execute("SELECT phash, ahash, dhash FROM fingerprints WHERE id = ?", (fp_id,))
        fp_row = cursor.fetchone()
        
        return {
            "id": fp_id,
            "evidence_id": evidence_id,
            "case_id": case_id,
            "filename": filename,
            "phash": fp_row["phash"] if fp_row else None,
            "embeddings_status": "Generated (CLIP-512)",
            "feature_status": "Extracted (ORB)",
            "url": f"/api/v1/evidence/file/{unique_filename}"
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.post("/fingerprint/video", status_code=202)
def fingerprint_video_endpoint(
    case_id: int = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer"]))
):
    """Enqueues video sequence fingerprinting as an asynchronous background job."""
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".mp4", ".mov", ".avi", ".mkv"]:
        raise HTTPException(status_code=400, detail="Unsupported video format container.")
        
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    unique_filename = f"{uuid.uuid4()}{ext}"
    target_path = os.path.join(EVIDENCE_DIR, unique_filename)
    
    # Save video file
    content = file.file.read()
    file_size = len(content)
    import hashlib
    sha256_hash = hashlib.sha256(content).hexdigest()
    with open(target_path, "wb") as f:
        f.write(content)
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM cases WHERE id = ?", (case_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Case not found.")
            
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_type = file.content_type or "video/mp4"
        
        # Register evidence item
        cursor.execute("""
            INSERT INTO evidence (case_id, platform, url, title, uploader, upload_date, status, screenshot_path, file_type, file_size, sha256_hash)
            VALUES (?, 'Other', ?, ?, ?, ?, 'Detected', ?, ?, ?, ?)
        """, (case_id, f"/api/v1/evidence/file/{unique_filename}", filename, user["username"], now_str, f"/storage/evidence/{unique_filename}", file_type, file_size, sha256_hash))
        
        evidence_id = cursor.lastrowid
        
        # Enqueue background job
        payload_json = json.dumps({
            "evidence_id": evidence_id,
            "filepath": target_path
        })
        
        cursor.execute("""
            INSERT INTO background_jobs (case_id, job_type, status, payload_json, url, current_step)
            VALUES (?, 'fingerprint_video', 'Queued', ?, ?, 'Queued')
        """, (case_id, payload_json, f"/api/v1/evidence/file/{unique_filename}"))
        
        job_id = cursor.lastrowid
        conn.commit()
        
        return {
            "job_id": job_id,
            "evidence_id": evidence_id,
            "case_id": case_id,
            "job_type": "fingerprint_video",
            "status": "Queued",
            "message": "Async video fingerprint processing initiated."
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.post("/fingerprint/audio", status_code=201)
def fingerprint_audio_endpoint(
    case_id: int = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer"]))
):
    """Synchronously fingerprints an audio file and registers it as evidence."""
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    if ext not in [".mp3", ".wav", ".aac", ".flac", ".m4a"]:
        raise HTTPException(status_code=400, detail="Unsupported audio format.")
        
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    unique_filename = f"{uuid.uuid4()}{ext}"
    target_path = os.path.join(EVIDENCE_DIR, unique_filename)
    
    # Save audio file
    content = file.file.read()
    file_size = len(content)
    import hashlib
    sha256_hash = hashlib.sha256(content).hexdigest()
    with open(target_path, "wb") as f:
        f.write(content)
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM cases WHERE id = ?", (case_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Case not found.")
            
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        file_type = file.content_type or "audio/mpeg"
        
        # Insert evidence record
        cursor.execute("""
            INSERT INTO evidence (case_id, platform, url, title, uploader, upload_date, status, screenshot_path, file_type, file_size, sha256_hash)
            VALUES (?, 'Other', ?, ?, ?, ?, 'Detected', ?, ?, ?, ?)
        """, (case_id, f"/api/v1/evidence/file/{unique_filename}", filename, user["username"], now_str, f"/storage/evidence/{unique_filename}", file_type, file_size, sha256_hash))
        
        evidence_id = cursor.lastrowid
        conn.commit()
        
        # Ingest fingerprint via Orchestrator
        fp_id = AIServiceOrchestrator.ingest_fingerprint(case_id, "evidence", evidence_id, target_path)
        
        # Get duration dynamically if audio processing tool available, or mock
        duration = 0.0
        try:
            import cv2
            cap = cv2.VideoCapture(target_path)
            # Basic fallback for visual/media files
            duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS)
            cap.release()
        except Exception:
            pass
            
        return {
            "id": fp_id,
            "evidence_id": evidence_id,
            "case_id": case_id,
            "status": "Completed",
            "duration": round(duration, 2) if duration > 0 else 0.0,
            "embeddings": "Generated (Audio-128)"
        }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/fingerprint/{id}", status_code=200)
def get_fingerprint_details(
    id: int,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves all hashes and embedding details for a target fingerprint record."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, case_id, entity_type, entity_id, phash, ahash, dhash, metadata_hash, ocr_fingerprint, created_at
            FROM fingerprints WHERE id = ?
        """, (id,))
        fp = cursor.fetchone()
        
        if not fp:
            raise HTTPException(status_code=404, detail="Fingerprint record not found.")
            
        # Check image embeddings existence
        cursor.execute("SELECT model_name, dimensions FROM image_embeddings WHERE fingerprint_id = ?", (id,))
        image_embs = [dict(row) for row in cursor.fetchall()]
        
        # Check video embeddings sequence existence
        cursor.execute("SELECT model_name, frame_index, timestamp_sec FROM video_embeddings WHERE fingerprint_id = ?", (id,))
        video_embs = [dict(row) for row in cursor.fetchall()]
        
        # Check audio embeddings
        cursor.execute("SELECT model_name, timestamp_start, timestamp_end FROM audio_embeddings WHERE fingerprint_id = ?", (id,))
        audio_embs = [dict(row) for row in cursor.fetchall()]
        
        embeddings_list = []
        for emb in image_embs + video_embs + audio_embs:
            embeddings_list.append({
                "model": emb.get("model_name"),
                "dimensions": emb.get("dimensions", 512),
                "meta": {k: v for k, v in emb.items() if k not in ["model_name", "dimensions"]}
            })
            
        return {
            "id": fp["id"],
            "case_id": fp["case_id"],
            "entity_type": fp["entity_type"],
            "entity_id": fp["entity_id"],
            "hashes": {
                "phash": fp["phash"],
                "ahash": fp["ahash"],
                "dhash": fp["dhash"],
                "metadata_hash": fp["metadata_hash"]
            },
            "embeddings": embeddings_list,
            "ocr_fingerprint": fp["ocr_fingerprint"],
            "created_at": fp["created_at"]
        }
    finally:
        conn.close()

@router.get("/fingerprint/entity/{entity_type}/{entity_id}", status_code=200)
def get_fingerprint_by_entity(
    entity_type: str,
    entity_id: int,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves fingerprint details for a given entity type and entity ID."""
    if entity_type not in ["original", "evidence"]:
        raise HTTPException(status_code=400, detail="Invalid entity type.")
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM fingerprints WHERE entity_type = ? AND entity_id = ? ORDER BY id DESC LIMIT 1", (entity_type, entity_id))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="No fingerprint registry found for this entity.")
        fp_id = row[0]
    finally:
        conn.close()
        
    return get_fingerprint_details(fp_id, user)

@router.post("/similarity/check", status_code=200)
def check_similarity_endpoint(
    req: SimilarityCheckRequest,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer"]))
):
    """Compares the visual hashes and embeddings of two entities, logging the scan history."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Create scan history record
        cursor.execute("""
            INSERT INTO scan_history (case_id, scan_type, status, progress_percent, started_at)
            VALUES (?, 'all', 'processing', 50.0, CURRENT_TIMESTAMP)
        """, (req.case_id,))
        scan_id = cursor.lastrowid
        conn.commit()
        
        res = AIServiceOrchestrator.check_similarity(
            req.case_id,
            req.source_id,
            req.source_type,
            req.target_id,
            req.target_type,
            req.match_types
        )
        
        if "error" in res:
            cursor.execute("""
                UPDATE scan_history
                SET status = 'failed', error_message = ?, progress_percent = 100.0, completed_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (res["error"], scan_id))
            conn.commit()
            raise HTTPException(status_code=400, detail=res["error"])
            
        # Log similarity result
        match_type = "hybrid"
        if len(req.match_types) == 1:
            match_type = req.match_types[0]
            
        cursor.execute("""
            INSERT INTO similarity_results (scan_id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, match_type, similarity_score, match_details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (scan_id, req.source_type, req.source_id, req.target_type, req.target_id, match_type, res["overall_score"], json.dumps(res["matches"])))
        
        cursor.execute("""
            UPDATE scan_history
            SET status = 'completed', progress_percent = 100.0, completed_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (scan_id,))
        
        conn.commit()
        return res
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@router.get("/similarity/history", status_code=200)
def get_similarity_history(
    case_id: Optional[int] = None,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Returns the historical record of similarity scan checks."""
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        if case_id:
            cursor.execute("""
                SELECT sr.id, sh.id as scan_id, sr.source_entity_id as source_id, sr.target_entity_id as target_id, sr.similarity_score, sr.match_type, sr.created_at
                FROM similarity_results sr
                JOIN scan_history sh ON sr.scan_id = sh.id
                WHERE sh.case_id = ?
                ORDER BY sr.id DESC
            """, (case_id,))
        else:
            cursor.execute("""
                SELECT sr.id, sh.id as scan_id, sr.source_entity_id as source_id, sr.target_entity_id as target_id, sr.similarity_score, sr.match_type, sr.created_at
                FROM similarity_results sr
                JOIN scan_history sh ON sr.scan_id = sh.id
                ORDER BY sr.id DESC
            """)
            
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
