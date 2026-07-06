import time
import json
import os
import sqlite3
from datetime import datetime
from backend.database import get_db_connection
from backend.fingerprint import compute_fingerprint, compare_fingerprints, generate_side_by_side_evidence
from backend.downloader import fetch_metadata, download_video_for_analysis, download_thumbnail
from backend.config import Config

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_DIR = os.path.join(PROJECT_ROOT, Config.STORAGE_DIR, "evidence")

def process_fingerprint_original(case_id, payload):
    original_id = payload["original_id"]
    filepath = payload["filepath"]
    
    if not os.path.exists(filepath):
         raise FileNotFoundError(f"Original video file not found at {filepath}")
         
    # Compute visual, scene, audio fingerprints
    analysis = compute_fingerprint(filepath)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE originals 
        SET filesize = ?, duration = ?, fingerprint_json = ?
        WHERE id = ?
    """, (analysis["filesize"], analysis["duration"], json.dumps(analysis), original_id))
    
    conn.commit()
    conn.close()
    print(f"[WORKER] Successfully generated visual & acoustic fingerprints for original video ID {original_id}.")

def process_scan_link(case_id, payload, job_id):
    url = payload["url"]
    user_id = payload["user_id"]
    
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    
    # 1. Fetch metadata
    metadata = fetch_metadata(url)
    if "error" in metadata and not metadata.get("title"):
         raise ValueError(f"Could not scan URL metadata: {metadata.get('error')}")
         
    platform = metadata["platform"]
    title = metadata["title"]
    uploader = metadata["uploader"]
    upload_date = metadata["upload_date"]
    thumbnail_url = metadata["thumbnail_url"]
    
    # Generate unique ID/prefix for local filenames
    url_hash = abs(hash(url))
    name_prefix = f"ev_{case_id}_{url_hash}"
    
    # 2. Download thumbnail
    local_screenshot_path = None
    if thumbnail_url:
        screenshot_full_path = download_thumbnail(thumbnail_url, EVIDENCE_DIR, name_prefix)
        if screenshot_full_path:
            local_screenshot_path = f"/storage/evidence/{os.path.basename(screenshot_full_path)}"
            
    # 3. Download low-resolution video for fingerprint matching
    temp_video_path = None
    similarity_score = 0.0
    matched_original_id = None
    best_match_offset = 0
    
    try:
        temp_video_path = download_video_for_analysis(url, EVIDENCE_DIR)
        
        # Calculate fingerprint for downloaded leak
        evidence_analysis = compute_fingerprint(temp_video_path)
        
        # Compare with all original videos for the case
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, fingerprint_json, file_uuid FROM originals WHERE case_id = ?", (case_id,))
        originals = cursor.fetchall()
        
        for orig in originals:
            orig_id = orig["id"]
            orig_name = orig["filename"]
            orig_uuid = orig["file_uuid"]
            orig_fp_str = orig["fingerprint_json"]
            
            if orig_fp_str and orig_fp_str != "[]":
                orig_fp_data = json.loads(orig_fp_str)
                score, details = compare_fingerprints(orig_fp_data, evidence_analysis)
                
                if score > similarity_score:
                    similarity_score = score
                    matched_original_id = orig_id
                    best_match_offset = details.get("best_match_offset_sec", 0)
                    
                    # If similarity is high, generate side-by-side evidence comparison
                    if score >= 0.80:
                         # Resolve original video physical file path
                         original_filename = None
                         original_dir = os.path.join(PROJECT_ROOT, Config.STORAGE_DIR, "originals")
                         for f in os.listdir(original_dir):
                              if f.startswith(orig_uuid):
                                   original_filename = f
                                   break
                         if original_filename:
                              orig_physical_path = os.path.join(original_dir, original_filename)
                              evidence_proof_filename = f"proof_{case_id}_{url_hash}.jpg"
                              evidence_proof_path = os.path.join(EVIDENCE_DIR, evidence_proof_filename)
                              
                              # Draw visual proof frame comparison
                              generated = generate_side_by_side_evidence(
                                   orig_physical_path, 
                                   temp_video_path, 
                                   best_match_offset, # Original frame offset match
                                   0.0, # Target leak frame offset
                                   evidence_proof_path
                              )
                              if generated:
                                   local_screenshot_path = f"/storage/evidence/{evidence_proof_filename}"
                                   
        conn.close()
    except Exception as e:
        print(f"[WORKER] Error during similarity comparison: {e}")
        # Proceed to log record even if download fails, with score 0.0
    finally:
        if temp_video_path and os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
            except Exception:
                pass
                
    # 4. Save evidence result in DB
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO evidence (case_id, platform, url, title, uploader, upload_date, similarity_score, status, screenshot_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        case_id,
        platform,
        url,
        title,
        uploader,
        upload_date,
        round(similarity_score, 4),
        "Verified" if similarity_score >= 0.80 else "Detected",
        local_screenshot_path
    ))
    evidence_id = cursor.lastrowid
    
    # Log user action in audit trails
    cursor.execute("""
        INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
        VALUES (?, 'LINK_SCAN_COMPLETE', 'evidence', ?, ?)
    """, (user_id, evidence_id, json.dumps({"url": url, "score": similarity_score})))
    
    conn.commit()
    conn.close()
    print(f"[WORKER] Completed scan for link {url} (Similarity Score: {similarity_score}).")

def worker_loop():
    """Main worker queue polling cycle."""
    print("[WORKER] Background queue worker initialized and monitoring jobs database.")
    while True:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Fetch oldest queued job
            cursor.execute("""
                SELECT id, case_id, job_type, payload_json 
                FROM background_jobs 
                WHERE status = 'Queued' 
                ORDER BY created_at ASC 
                LIMIT 1
            """)
            job = cursor.fetchone()
            
            if job:
                job_id = job["id"]
                case_id = job["case_id"]
                job_type = job["job_type"]
                payload = json.loads(job["payload_json"])
                
                # Mark job as Processing
                started_at = datetime.utcnow().isoformat()
                cursor.execute("""
                    UPDATE background_jobs 
                    SET status = 'Processing', started_at = ? 
                    WHERE id = ?
                """, (started_at, job_id))
                conn.commit()
                
                print(f"[WORKER] Starting job {job_id} ({job_type}) for Case {case_id}.")
                
                # Process the job
                error_msg = None
                try:
                    if job_type == 'fingerprint_original':
                        process_fingerprint_original(case_id, payload)
                    elif job_type == 'scan_link':
                        process_scan_link(case_id, payload, job_id)
                except Exception as ex:
                    error_msg = str(ex)
                    print(f"[WORKER] Job {job_id} failed with error: {error_msg}")
                    
                # Mark job as Completed or Failed
                completed_at = datetime.utcnow().isoformat()
                if error_msg:
                    cursor.execute("""
                        UPDATE background_jobs 
                        SET status = 'Failed', error_message = ?, completed_at = ? 
                        WHERE id = ?
                    """, (error_msg, completed_at, job_id))
                else:
                    cursor.execute("""
                        UPDATE background_jobs 
                        SET status = 'Completed', completed_at = ? 
                        WHERE id = ?
                    """, (completed_at, job_id))
                conn.commit()
                
            conn.close()
        except Exception as e:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            print(f"[WORKER] Loop encountered database error: {e}")
            
        time.sleep(2.0)

if __name__ == "__main__":
    worker_loop()
