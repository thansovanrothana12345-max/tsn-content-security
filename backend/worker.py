import time
import json
import os
import sqlite3
from datetime import datetime
from backend.database import get_db_connection
from backend.fingerprint import compute_fingerprint, compare_fingerprints, generate_side_by_side_evidence
from backend.downloader import fetch_metadata, download_video_for_analysis, download_thumbnail
from backend.config import Config
from backend.ai.services.orchestrator import AIServiceOrchestrator

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EVIDENCE_DIR = os.path.join(PROJECT_ROOT, Config.STORAGE_DIR, "evidence")

def update_job_progress(job_id, progress_percent, current_step, status="Processing"):
    if not job_id:
        return
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE background_jobs
            SET status = ?, progress_percent = ?, current_step = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (status, progress_percent, current_step, job_id))
        conn.commit()
    except Exception as e:
        print(f"[WORKER] Failed to update job progress for job {job_id}: {e}")
    finally:
        conn.close()

def is_job_cancelled(job_id):
    if not job_id:
        return False
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM background_jobs WHERE id = ?", (job_id,))
        row = cursor.fetchone()
        if row and row["status"] == "Cancelled":
            return True
        return False
    finally:
        conn.close()

def process_fingerprint_original(case_id, payload, job_id=None):
    if is_job_cancelled(job_id):
        raise InterruptedError("Job cancelled by user.")
        
    original_id = payload["original_id"]
    filepath = payload["filepath"]
    
    if not os.path.exists(filepath):
         raise FileNotFoundError(f"Original video file not found at {filepath}")
         
    # Compute visual, scene, audio fingerprints
    update_job_progress(job_id, 25.0, "Generating Fingerprint")
    if is_job_cancelled(job_id):
        raise InterruptedError("Job cancelled by user.")
    analysis = compute_fingerprint(filepath)
    
    update_job_progress(job_id, 75.0, "Saving Evidence")
    if is_job_cancelled(job_id):
        raise InterruptedError("Job cancelled by user.")
        
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
    if is_job_cancelled(job_id):
        raise InterruptedError("Job cancelled by user.")
        
    url = payload["url"]
    user_id = payload["user_id"]
    
    os.makedirs(EVIDENCE_DIR, exist_ok=True)
    
    # 1. Fetch metadata
    update_job_progress(job_id, 10.0, "Fetching Metadata")
    if is_job_cancelled(job_id):
        raise InterruptedError("Job cancelled by user.")
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
        if is_job_cancelled(job_id):
            raise InterruptedError("Job cancelled by user.")
        screenshot_full_path = download_thumbnail(thumbnail_url, EVIDENCE_DIR, name_prefix)
        if screenshot_full_path:
            local_screenshot_path = f"/storage/evidence/{os.path.basename(screenshot_full_path)}"
            
    # 3. Download low-resolution video for fingerprint matching
    temp_video_path = None
    similarity_score = 0.0
    matched_original_id = None
    best_match_offset = 0
    
    try:
        update_job_progress(job_id, 25.0, "Downloading Video")
        if is_job_cancelled(job_id):
            raise InterruptedError("Job cancelled by user.")
        temp_video_path = download_video_for_analysis(url, EVIDENCE_DIR)
        
        # Calculate fingerprint for downloaded leak
        update_job_progress(job_id, 50.0, "Generating Fingerprint")
        if is_job_cancelled(job_id):
            raise InterruptedError("Job cancelled by user.")
        evidence_analysis = compute_fingerprint(temp_video_path)
        
        # Compare with all original videos for the case
        update_job_progress(job_id, 70.0, "Comparing Fingerprints")
        if is_job_cancelled(job_id):
            raise InterruptedError("Job cancelled by user.")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, filename, fingerprint_json, file_uuid FROM originals WHERE case_id = ?", (case_id,))
        originals = cursor.fetchall()
        
        for orig in originals:
            if is_job_cancelled(job_id):
                raise InterruptedError("Job cancelled by user.")
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
        raise e
    finally:
        if temp_video_path and os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
            except Exception:
                pass
                
    # 4. Save evidence result in DB
    update_job_progress(job_id, 90.0, "Saving Evidence")
    if is_job_cancelled(job_id):
        raise InterruptedError("Job cancelled by user.")
        
    # Calculate sha256 hash for enqueued evidence
    sha_hash = None
    if local_screenshot_path:
        fn = os.path.basename(local_screenshot_path)
        phys_path = os.path.join(EVIDENCE_DIR, fn)
        if os.path.exists(phys_path):
            import hashlib
            try:
                h = hashlib.sha256()
                with open(phys_path, "rb") as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        h.update(chunk)
                sha_hash = h.hexdigest()
            except Exception:
                pass
    if not sha_hash:
        import hashlib
        sha_hash = hashlib.sha256(url.encode('utf-8', errors='ignore')).hexdigest()

    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        INSERT INTO evidence (case_id, platform, url, title, uploader, upload_date, similarity_score, status, screenshot_path, sha256_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        case_id,
        platform,
        url,
        title,
        uploader,
        upload_date,
        round(similarity_score, 4),
        "Verified" if similarity_score >= 0.80 else "Detected",
        local_screenshot_path,
        sha_hash
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

def process_fingerprint_video_job(case_id, payload, job_id):
    if is_job_cancelled(job_id):
        raise InterruptedError("Job cancelled by user.")
        
    evidence_id = payload["evidence_id"]
    filepath = payload["filepath"]
    
    update_job_progress(job_id, 20.0, "Extracting Video Frames")
    if is_job_cancelled(job_id):
        raise InterruptedError("Job cancelled by user.")
        
    AIServiceOrchestrator.ingest_fingerprint(case_id, "evidence", evidence_id, filepath)
    
    update_job_progress(job_id, 100.0, "Completed", status="Completed")
    print(f"[WORKER] Successfully generated visual sequence fingerprints for video ID {evidence_id}.")

def process_fingerprint_audio_job(case_id, payload, job_id):
    if is_job_cancelled(job_id):
        raise InterruptedError("Job cancelled by user.")
        
    evidence_id = payload["evidence_id"]
    filepath = payload["filepath"]
    
    update_job_progress(job_id, 30.0, "Computing Audio FFT")
    if is_job_cancelled(job_id):
        raise InterruptedError("Job cancelled by user.")
        
    AIServiceOrchestrator.ingest_fingerprint(case_id, "evidence", evidence_id, filepath)
    
    update_job_progress(job_id, 100.0, "Completed", status="Completed")
    print(f"[WORKER] Successfully generated audio fingerprints for ID {evidence_id}.")

def update_scan_job_progress(job_id, progress_percent, status="Running", error_message=None):
    if not job_id:
        return
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        if status == "Running":
            cursor.execute("""
                UPDATE scan_jobs
                SET status = ?, progress_percent = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, progress_percent, job_id))
        elif status == "Completed":
            cursor.execute("""
                UPDATE scan_jobs
                SET status = ?, progress_percent = 100.0, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, job_id))
        elif status == "Failed":
            cursor.execute("""
                UPDATE scan_jobs
                SET status = ?, progress_percent = 100.0, error_message = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (status, error_message, job_id))
        conn.commit()
    except Exception as e:
        print(f"[WORKER] Failed to update scan_job progress for job {job_id}: {e}")
    finally:
        conn.close()

def process_single_scan_job(job):
    from backend.services.connectors import get_connector_for_url
    from backend.services.logger import log_scan_job, log_evidence, log_worker, log_connector
    
    job_id = job["id"]
    url = job["url"]
    case_id = job["case_id"]
    user_id = job["created_by"] or 0
    
    log_worker("START_SCAN_JOB", f"Job ID {job_id} starting for URL: {url}")
    log_scan_job("START", job_id, "Running", f"URL: {url}")
    update_scan_job_progress(job_id, 10.0, status="Running")
    
    try:
        connector = get_connector_for_url(url)
        platform = job.get("platform", "Unknown")
        
        # 1. Fetch Metadata (with retry loops)
        update_scan_job_progress(job_id, 30.0)
        
        retry_count = 0
        max_retries = Config.QUEUE_MAX_RETRIES
        backoff = 2.0
        metadata = None
        
        while retry_count <= max_retries:
            try:
                log_connector(platform, "METADATA_FETCH", f"Fetching metadata (Attempt {retry_count + 1}/{max_retries + 1})")
                metadata = connector.extract_metadata(url)
                if "error" in metadata and not metadata.get("title"):
                    raise ValueError(f"Could not parse URL metadata: {metadata.get('error')}")
                break
            except Exception as e:
                retry_count += 1
                if retry_count > max_retries:
                    log_connector(platform, "METADATA_FETCH_FAILED", f"Final attempt failed for url {url}: {e}", status="ERROR")
                    raise e
                sleep_time = backoff ** retry_count
                log_connector(platform, "METADATA_FETCH_RETRY", f"Attempt failed: {e}. Retrying in {sleep_time}s...", status="WARNING")
                time.sleep(sleep_time)
                
        platform = metadata.get("platform", platform)
        title = metadata["title"]
        uploader = metadata["uploader"]
        upload_date = metadata["upload_date"]
        
        # Generate prefix
        name_prefix = f"scan_{job_id}_{abs(hash(url))}"
        
        # 2. Download Screenshot/Thumbnail (with retry loops)
        update_scan_job_progress(job_id, 60.0)
        screenshot_full_path = None
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                log_connector(platform, "DOWNLOAD_SCREENSHOT", f"Downloading screenshot (Attempt {retry_count + 1}/{max_retries + 1})")
                screenshot_full_path = connector.download_screenshot(url, EVIDENCE_DIR, name_prefix)
                break
            except Exception as e:
                retry_count += 1
                if retry_count > max_retries:
                    log_connector(platform, "DOWNLOAD_SCREENSHOT_FAILED", f"Screenshot download failed: {e}", status="ERROR")
                    break
                time.sleep(backoff ** retry_count)
                
        screenshot_relative_path = None
        if screenshot_full_path:
            screenshot_relative_path = f"/storage/evidence/{os.path.basename(screenshot_full_path)}"
            
        # 3. Download low-resolution video/asset (if supported by connector)
        update_scan_job_progress(job_id, 80.0)
        try:
            log_connector(platform, "DOWNLOAD_ASSET", f"Downloading low-res asset for fingerprinting")
            connector.download_asset(url, EVIDENCE_DIR)
        except Exception as ex:
            log_connector(platform, "DOWNLOAD_ASSET_OMITTED", f"Asset download omitted or failed: {ex}")
            
        # Save results in database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO scan_results (job_id, url, platform, title, uploader, upload_date, metadata_json, screenshot_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """, (job_id, url, platform, title, uploader, upload_date, json.dumps(metadata), screenshot_relative_path))
        scan_result_id = cursor.lastrowid
        
        # Automatically create or link to case
        target_case_id = case_id
        if not target_case_id:
            case_title = f"{platform} - {uploader or 'Auto Case'}"
            cursor.execute("SELECT id FROM cases WHERE title = ? AND is_deleted = 0;", (case_title,))
            case_row = cursor.fetchone()
            if case_row:
                target_case_id = case_row["id"]
            else:
                cursor.execute("""
                    INSERT INTO cases (title, description, status, priority)
                    VALUES (?, ?, 'Investigating', 'Medium');
                """, (case_title, f"Auto-created case for scans from uploader {uploader} on {platform}"))
                target_case_id = cursor.lastrowid
                
        # Generate hash of url for evidence mapping
        import hashlib
        sha_hash = hashlib.sha256(url.encode('utf-8', errors='ignore')).hexdigest()
        
        # Create immutable Evidence record
        cursor.execute("""
            INSERT INTO evidence (case_id, platform, url, title, uploader, upload_date, status, screenshot_path, sha256_hash)
            VALUES (?, ?, ?, ?, ?, ?, 'Detected', ?, ?);
        """, (target_case_id, platform, url, title, uploader, upload_date, screenshot_relative_path, sha_hash))
        evidence_id = cursor.lastrowid
        
        # Link in case_evidence junction
        cursor.execute("""
            INSERT INTO case_evidence (case_id, evidence_id)
            VALUES (?, ?);
        """, (target_case_id, evidence_id))
        
        # Write to audit logs
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
            VALUES (?, 'CREATE_EVIDENCE', 'evidence', ?, ?);
        """, (user_id, evidence_id, json.dumps({"url": url, "case_id": target_case_id})))
        
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
            VALUES (?, 'SCAN_JOB_COMPLETE', 'scan_job', ?, ?);
        """, (user_id, job_id, json.dumps({"url": url})))
        
        conn.commit()
        conn.close()
        
        update_scan_job_progress(job_id, 100.0, status="Completed")
        log_scan_job("COMPLETE", job_id, "Completed", f"Matched Evidence ID {evidence_id}")
        log_worker("COMPLETE_SCAN_JOB", f"Job ID {job_id} completed successfully.")
        
    except Exception as e:
        error_msg = str(e)
        log_worker("SCAN_JOB_ERROR", f"Job ID {job_id} failed: {error_msg}", status="ERROR")
        log_scan_job("FAIL", job_id, "Failed", f"Error: {error_msg}")
        update_scan_job_progress(job_id, 100.0, status="Failed", error_message=error_msg)

def worker_loop():
    """Main worker queue polling cycle."""
    print("[WORKER] Background queue worker initialized and monitoring jobs database.")
    while True:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 1. Fetch oldest queued legacy job
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
                    SET status = 'Processing', started_at = ?, progress_percent = 5.0, current_step = 'Queued', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (started_at, job_id))
                conn.commit()
                
                print(f"[WORKER] Starting job {job_id} ({job_type}) for Case {case_id}.")
                
                # Process the job
                error_msg = None
                try:
                    if job_type == 'fingerprint_original':
                        process_fingerprint_original(case_id, payload, job_id)
                    elif job_type == 'scan_link':
                        process_scan_link(case_id, payload, job_id)
                    elif job_type == 'fingerprint_video':
                        process_fingerprint_video_job(case_id, payload, job_id)
                    elif job_type == 'fingerprint_audio':
                        process_fingerprint_audio_job(case_id, payload, job_id)
                except Exception as ex:
                    error_msg = str(ex)
                    print(f"[WORKER] Job {job_id} failed with error: {error_msg}")
                    
                # Mark job as Completed or Failed (if not cancelled)
                cursor.execute("SELECT status, started_at FROM background_jobs WHERE id = ?", (job_id,))
                status_row = cursor.fetchone()
                current_status = status_row["status"] if status_row else "Processing"
                start_iso = status_row["started_at"] if status_row else started_at
                
                completed_at = datetime.utcnow().isoformat()
                
                # Compute duration
                duration_val = None
                if start_iso:
                    try:
                        start_dt = datetime.fromisoformat(start_iso)
                        end_dt = datetime.fromisoformat(completed_at)
                        duration_val = (end_dt - start_dt).total_seconds()
                    except Exception:
                        pass
                
                if current_status == "Cancelled":
                    # Keep cancelled state but compute duration and timestamps
                    cursor.execute("""
                        UPDATE background_jobs 
                        SET completed_at = ?, finished_at = ?, duration = ?, progress_percent = 100.0, current_step = 'Cancelled', updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (completed_at, completed_at, duration_val, job_id))
                elif error_msg:
                    if "cancelled by user" in error_msg.lower() or "interrupted" in error_msg.lower():
                        cursor.execute("""
                            UPDATE background_jobs 
                            SET status = 'Cancelled', completed_at = ?, finished_at = ?, duration = ?, progress_percent = 100.0, current_step = 'Cancelled', updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (completed_at, completed_at, duration_val, job_id))
                    else:
                        cursor.execute("""
                            UPDATE background_jobs 
                            SET status = 'Failed', error_message = ?, completed_at = ?, finished_at = ?, duration = ?, progress_percent = 100.0, current_step = 'Failed', updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (error_msg, completed_at, completed_at, duration_val, job_id))
                else:
                    cursor.execute("""
                        UPDATE background_jobs 
                        SET status = 'Completed', completed_at = ?, finished_at = ?, duration = ?, progress_percent = 100.0, current_step = 'Completed', updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (completed_at, completed_at, duration_val, job_id))
                conn.commit()
                
            # 2. Fetch oldest queued Scan Center job
            cursor.execute("""
                SELECT id, case_id, url, platform, created_by
                FROM scan_jobs
                WHERE status = 'Pending'
                ORDER BY created_at ASC
                LIMIT 1
            """)
            scan_job = cursor.fetchone()
            if scan_job:
                # Close connection while running the job to release DB locks
                conn.close()
                conn = None
                process_single_scan_job(dict(scan_job))
                
            if conn:
                conn.close()
        except Exception as e:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass
            print(f"[WORKER] Loop encountered database error: {e}")
            
        time.sleep(Config.QUEUE_POLLING_INTERVAL)

if __name__ == "__main__":
    worker_loop()
