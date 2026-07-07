from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends
from fastapi.responses import StreamingResponse
import io
from pydantic import BaseModel
import os
import shutil
import uuid
import json
import hashlib
import cv2
from typing import Optional
from backend.database import get_db_connection
from backend.routes.auth import require_role
from backend.config import Config

router = APIRouter(prefix="/api/v1/originals", tags=["Originals"])

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMP_DIR = os.path.join(PROJECT_ROOT, Config.STORAGE_DIR, "temp")
ORIGINALS_DIR = os.path.join(PROJECT_ROOT, Config.STORAGE_DIR, "originals")

class AssembleRequest(BaseModel):
    case_id: int
    upload_uuid: str
    filename: str
    checksum: Optional[str] = None # Optional MD5 checksum to verify chunk assembly

def get_video_duration(filepath: str) -> float:
    """Uses OpenCV to extract the video duration in seconds."""
    try:
        cap = cv2.VideoCapture(filepath)
        if not cap.isOpened():
            return 0.0
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        cap.release()
        if fps > 0:
            return float(frame_count / fps)
    except Exception:
        pass
    return 0.0

def register_original_in_db(case_id: int, safe_filename: str, file_uuid: str, filesize: int, duration: float, destination_path: str, user: dict) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify case folder exists
    cursor.execute("SELECT id FROM cases WHERE id = ?", (case_id,))
    if not cursor.fetchone():
        conn.close()
        if os.path.exists(destination_path):
            os.remove(destination_path)
        raise HTTPException(status_code=404, detail="Case folder not found.")
        
    try:
        # Save to SQLite originals registry
        cursor.execute(
            """
            INSERT INTO originals (case_id, filename, file_uuid, storage_provider, filesize, duration, fingerprint_json)
            VALUES (?, ?, ?, 'local', ?, ?, '[]')
            """,
            (case_id, safe_filename, file_uuid, filesize, duration)
        )
        original_id = cursor.lastrowid
        
        # Log audit entry
        details = json.dumps({"filename": safe_filename, "file_uuid": file_uuid, "filesize": filesize, "duration": duration})
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
            VALUES (?, 'UPLOAD_ORIGINAL', 'original', ?, ?)
        """, (user["id"], original_id, details))
        
        # Enqueue background fingerprint job
        job_payload = json.dumps({"original_id": original_id, "filepath": destination_path})
        cursor.execute("""
            INSERT INTO background_jobs (case_id, job_type, status, payload_json)
            VALUES (?, 'fingerprint_original', 'Queued', ?)
        """, (case_id, job_payload))
        
        conn.commit()
        return original_id
    except sqlite3.Error as e:
        conn.close()
        if os.path.exists(destination_path):
            os.remove(destination_path)
        raise HTTPException(status_code=500, detail=f"Database write error: {str(e)}")
    finally:
        conn.close()

# 1. List originals for a case
@router.get("/{case_id}")
def list_originals(case_id: int, user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, case_id, filename, file_uuid, storage_provider, filesize, duration, created_at 
            FROM originals 
            WHERE case_id = ? 
            ORDER BY created_at DESC
        """, (case_id,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

# 2. Upload Chunk
@router.post("/upload/chunk")
async def upload_chunk(
    upload_uuid: str = Form(...),
    chunk_index: int = Form(...),
    total_chunks: int = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    # Basic directory path validation
    safe_uuid = "".join(c for c in upload_uuid if c.isalnum() or c in "-")
    chunk_dir = os.path.join(TEMP_DIR, safe_uuid)
    os.makedirs(chunk_dir, exist_ok=True)
    
    chunk_path = os.path.join(chunk_dir, str(chunk_index))
    
    # Save the chunk file
    try:
        with open(chunk_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save video chunk: {str(e)}")
        
    return {"message": f"Chunk {chunk_index}/{total_chunks} uploaded successfully."}

# 3. Assemble Chunks
@router.post("/upload/assemble")
async def assemble_chunks(request: AssembleRequest, user: dict = Depends(require_role(["Admin", "Editor"]))):
    safe_uuid = "".join(c for c in request.upload_uuid if c.isalnum() or c in "-")
    chunk_dir = os.path.join(TEMP_DIR, safe_uuid)
    
    if not os.path.exists(chunk_dir):
        raise HTTPException(status_code=400, detail="Upload UUID directory does not exist.")
        
    # Get all chunk files in order
    try:
        chunks = sorted([int(f) for f in os.listdir(chunk_dir) if f.isdigit()])
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid chunk filename detected.")
        
    if not chunks:
        raise HTTPException(status_code=400, detail="No chunks found to assemble.")
        
    # Generate unique UUID for the assembled original video file
    file_uuid = str(uuid.uuid4())
    # Sanitize file name
    safe_filename = "".join(c for c in request.filename if c.isalnum() or c in "._- ")
    if not safe_filename:
         safe_filename = f"{file_uuid}.mp4"
         
    file_ext = os.path.splitext(safe_filename)[1].lower()
    if file_ext not in [".mp4", ".mkv", ".avi"]:
         # Default to .mp4 container format
         file_ext = ".mp4"
         
    destination_filename = f"{file_uuid}{file_ext}"
    destination_path = os.path.join(ORIGINALS_DIR, destination_filename)
    
    # Assemble chunks sequentially
    try:
        with open(destination_path, "wb") as dest_file:
            for idx in range(len(chunks)):
                chunk_file_path = os.path.join(chunk_dir, str(idx))
                if not os.path.exists(chunk_file_path):
                    # Clean up
                    if os.path.exists(destination_path):
                         os.remove(destination_path)
                    raise HTTPException(status_code=400, detail=f"Missing chunk index {idx} in sequence.")
                    
                with open(chunk_file_path, "rb") as chunk_file:
                    dest_file.write(chunk_file.read())
    except Exception as e:
        if os.path.exists(destination_path):
            os.remove(destination_path)
        raise HTTPException(status_code=500, detail=f"Failed to assemble video file: {str(e)}")
        
    # Verify file MD5 if checksum is provided
    if request.checksum:
        md5_hash = hashlib.md5()
        with open(destination_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        calculated_checksum = md5_hash.hexdigest()
        if calculated_checksum.lower() != request.checksum.lower():
            if os.path.exists(destination_path):
                 os.remove(destination_path)
            raise HTTPException(status_code=400, detail="Checksum verification failed. File may be corrupted.")
            
    # Calculate file size & duration
    filesize = os.path.getsize(destination_path)
    
    # Check max file size bounds (2GB limit)
    if filesize > 2 * 1024 * 1024 * 1024:
         if os.path.exists(destination_path):
              os.remove(destination_path)
         raise HTTPException(status_code=400, detail="File size exceeds the 2GB limit.")
         
    duration = get_video_duration(destination_path)
    
    original_id = register_original_in_db(
        case_id=request.case_id,
        safe_filename=safe_filename,
        file_uuid=file_uuid,
        filesize=filesize,
        duration=duration,
        destination_path=destination_path,
        user=user
    )
    
    # Clean up temporary chunk files directory
    try:
        shutil.rmtree(chunk_dir)
    except Exception as err:
        print(f"Error cleaning chunk uploads folder: {err}")
        
    return {
        "id": original_id,
        "filename": safe_filename,
        "file_uuid": file_uuid,
        "filesize": filesize,
        "duration": duration,
        "message": "Original video successfully uploaded and assembled."
    }

# 4. Delete Original
@router.delete("/{original_id}")
def delete_original(original_id: int, user: dict = Depends(require_role(["Admin"]))):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT case_id, filename, file_uuid, storage_provider FROM originals WHERE id = ?", (original_id,))
    row = cursor.fetchone()
    
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Original video record not found.")
        
    # Delete from database
    cursor.execute("DELETE FROM originals WHERE id = ?", (original_id,))
    
    # Clean up related background jobs, duplicate groups, and duplicate group members
    cursor.execute("DELETE FROM background_jobs WHERE job_type = 'fingerprint_original' AND payload_json LIKE ?;", (f'%"original_id": {original_id}%',))
    
    file_uuid = row["file_uuid"]
    cursor.execute("DELETE FROM duplicate_groups WHERE representative_file_uuid = ? AND representative_file_type = 'original';", (file_uuid,))
    cursor.execute("DELETE FROM duplicate_group_members WHERE member_file_uuid = ? AND member_file_type = 'original';", (file_uuid,))
    
    # Log audit entry
    details = json.dumps({"filename": row["filename"], "file_uuid": row["file_uuid"]})
    cursor.execute("""
        INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
        VALUES (?, 'DELETE_ORIGINAL', 'original', ?, ?)
    """, (user["id"], original_id, details))
    
    conn.commit()
    conn.close()
    
    # Delete local physical file if storage provider is local
    if row["storage_provider"] == "local":
        # Search for file matching file_uuid
        for file in os.listdir(ORIGINALS_DIR):
             if file.startswith(row["file_uuid"]):
                 file_path = os.path.join(ORIGINALS_DIR, file)
                 if os.path.exists(file_path):
                      try:
                          os.remove(file_path)
                      except Exception as err:
                          print(f"Error deleting physical file: {err}")
                          
    return {"message": f"Original video {original_id} successfully deleted."}

# 5. Get Original Frame Scrubbing
@router.get("/{original_id}/frame")
def get_original_frame(
    original_id: int, 
    offset: float, 
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Seeks to the offset in the original video and returns the frame as JPEG."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_uuid, storage_provider, filename FROM originals WHERE id = ?", (original_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(
            status_code=404, 
            detail={"error": "NOT_FOUND", "message": "Original video not found."}
        )
        
    if row["storage_provider"] != "local":
        raise HTTPException(
            status_code=400, 
            detail={"error": "BAD_REQUEST", "message": "Non-local storage providers not supported yet."}
        )
        
    # Resolve physical path
    original_filename = None
    for f in os.listdir(ORIGINALS_DIR):
        if f.startswith(row["file_uuid"]):
            original_filename = f
            break
            
    if not original_filename:
        raise HTTPException(
            status_code=404, 
            detail={"error": "NOT_FOUND", "message": "Video physical file not found."}
        )
        
    video_path = os.path.join(ORIGINALS_DIR, original_filename)
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise HTTPException(
            status_code=500, 
            detail={"error": "INTERNAL_ERROR", "message": "Could not open video file."}
        )
        
    # Get duration bounds
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    duration = frame_count / fps if (fps > 0 and frame_count > 0) else 0.0
    
    if offset < 0.0 or (duration > 0 and offset > duration):
        cap.release()
        raise HTTPException(
            status_code=400, 
            detail={"error": "BAD_REQUEST", "message": f"Offset out of video duration bounds (0 - {duration:.2f}s)."}
        )
        
    cap.set(cv2.CAP_PROP_POS_MSEC, offset * 1000)
    ret, frame = cap.read()
    cap.release()
    
    if not ret:
        raise HTTPException(
            status_code=500, 
            detail={"error": "INTERNAL_ERROR", "message": "Failed to decode frame at target offset."}
        )
        
    # Resize frame standardizing dimension
    h_target = 360
    w = int(frame.shape[1] * (h_target / frame.shape[0]))
    frame_resized = cv2.resize(frame, (w, h_target))
    
    # Encode as JPEG
    is_success, buffer = cv2.imencode(".jpg", frame_resized)
    if not is_success:
        raise HTTPException(
            status_code=500, 
            detail={"error": "INTERNAL_ERROR", "message": "Failed to encode frame as JPEG."}
        )
        
    io_buf = io.BytesIO(buffer)
    return StreamingResponse(io_buf, media_type="image/jpeg")

# 6. Single File Upload
@router.post("/upload")
async def upload_original_single(
    case_id: int = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    # Generate unique UUID for the original video file
    file_uuid = str(uuid.uuid4())
    safe_filename = "".join(c for c in file.filename if c.isalnum() or c in "._- ")
    if not safe_filename:
        safe_filename = f"{file_uuid}.mp4"
        
    file_ext = os.path.splitext(safe_filename)[1].lower()
    if file_ext not in [".mp4", ".mkv", ".avi"]:
        file_ext = ".mp4"
        
    destination_filename = f"{file_uuid}{file_ext}"
    destination_path = os.path.join(ORIGINALS_DIR, destination_filename)
    
    # Save file contents
    try:
        contents = await file.read()
        filesize = len(contents)
        if filesize > 2 * 1024 * 1024 * 1024: # 2GB Limit
            raise HTTPException(status_code=400, detail="File size exceeds the 2GB limit.")
            
        with open(destination_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        if os.path.exists(destination_path):
            os.remove(destination_path)
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded video: {str(e)}")
        
    duration = get_video_duration(destination_path)
    
    original_id = register_original_in_db(
        case_id=case_id,
        safe_filename=safe_filename,
        file_uuid=file_uuid,
        filesize=filesize,
        duration=duration,
        destination_path=destination_path,
        user=user
    )
    return {
        "id": original_id,
        "filename": safe_filename,
        "file_uuid": file_uuid,
        "filesize": filesize,
        "duration": duration,
        "message": "Original video successfully uploaded."
    }


class RegisterLicenseRequest(BaseModel):
    license_type: str
    licensee_name: Optional[str] = None
    allowed_platforms: Optional[list] = None
    geo_exclusions: Optional[list] = None
    expires_at: Optional[str] = None

@router.post("/{original_id}/license", status_code=201)
def set_original_license(
    original_id: int,
    request: RegisterLicenseRequest,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Sets or registers the license configuration for an original reference file."""
    from backend.services.asset_intelligence import AssetIntelligenceService
    try:
        license_id = AssetIntelligenceService.register_license(
            original_id=original_id,
            license_type=request.license_type,
            licensee_name=request.licensee_name,
            allowed_platforms=request.allowed_platforms,
            geo_exclusions=request.geo_exclusions,
            expires_at=request.expires_at
        )
        return {"license_id": license_id, "message": "Asset license successfully registered."}
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@router.get("/{original_id}/license")
def get_original_license(
    original_id: int,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Fetches the licensing details registered for an original reference file."""
    from backend.services.asset_intelligence import AssetIntelligenceService
    try:
        license_info = AssetIntelligenceService.get_license(original_id)
        if not license_info:
            raise HTTPException(status_code=404, detail="No license registered for this original reference asset.")
        return license_info
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
