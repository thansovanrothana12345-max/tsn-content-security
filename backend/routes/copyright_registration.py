import os
import uuid
import hashlib
import base64
import mimetypes
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional
from backend.database import get_db_connection
from backend.routes.auth import require_role
from backend.config import Config
from backend.fingerprint import extract_file_metadata

router = APIRouter(prefix="/api/v1/copyright", tags=["Copyright Registration"])

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEMP_DIR = os.path.join(PROJECT_ROOT, Config.STORAGE_DIR, "temp")
REG_DIR = os.path.join(PROJECT_ROOT, Config.STORAGE_DIR, "registrations")
THUMB_DIR = os.path.join(PROJECT_ROOT, Config.STORAGE_DIR, "thumbnails")

os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(REG_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)

# -------------------------------------------------------------
# Cryptographic Helpers (RC4 Salted Encryption for Private Data)
# -------------------------------------------------------------
def rc4_crypt(data: bytes, key: bytes) -> bytes:
    S = list(range(256))
    j = 0
    out = bytearray()
    for i in range(256):
        j = (j + S[i] + key[i % len(key)]) % 256
        S[i], S[j] = S[j], S[i]
    i = j = 0
    for char in data:
        i = (i + 1) % 256
        j = (j + S[i]) % 256
        S[i], S[j] = S[j], S[i]
        out.append(char ^ S[(S[i] + S[j]) % 256])
    return bytes(out)

def encrypt_field(plaintext: str) -> str:
    if not plaintext:
        return ""
    salt = os.urandom(16)
    key = hashlib.sha256(Config.SECRET_KEY.encode('utf-8') + salt).digest()
    ciphertext = rc4_crypt(plaintext.encode('utf-8'), key)
    combined = salt + ciphertext
    return base64.b64encode(combined).decode('utf-8')

def decrypt_field(encoded_text: str) -> str:
    if not encoded_text:
        return ""
    try:
        combined = base64.b64decode(encoded_text.encode('utf-8'))
        if len(combined) < 16:
            return ""
        salt = combined[:16]
        ciphertext = combined[16:]
        key = hashlib.sha256(Config.SECRET_KEY.encode('utf-8') + salt).digest()
        decrypted = rc4_crypt(ciphertext, key)
        return decrypted.decode('utf-8')
    except Exception:
        return "[DECRYPTION_ERROR]"

# -------------------------------------------------------------
# Thumbnail Generation Helpers
# -------------------------------------------------------------
def generate_thumbnail(file_path: str, category: str, file_uuid: str) -> str:
    thumb_filename = f"{file_uuid}.jpg"
    thumb_path = os.path.join(THUMB_DIR, thumb_filename)
    web_thumb_path = f"storage/thumbnails/{thumb_filename}"
    
    try:
        import cv2
        if category == "Video":
            cap = cv2.VideoCapture(file_path)
            if cap.isOpened():
                fps = cap.get(cv2.CAP_PROP_FPS)
                frame_idx = int(fps) if fps > 0 else 0
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                ret, frame = cap.read()
                if ret:
                    h, w = frame.shape[:2]
                    target_w = 120
                    target_h = int(h * (target_w / w))
                    resized = cv2.resize(frame, (target_w, target_h))
                    cv2.imwrite(thumb_path, resized)
                    cap.release()
                    return web_thumb_path
                cap.release()
        elif category == "Image":
            img = cv2.imread(file_path)
            if img is not None:
                h, w = img.shape[:2]
                target_w = 120
                target_h = int(h * (target_w / w))
                resized = cv2.resize(img, (target_w, target_h))
                cv2.imwrite(thumb_path, resized)
                return web_thumb_path
    except Exception as e:
        print(f"Thumbnail generation warning: {e}")
        
    return ""

# -------------------------------------------------------------
# Data Models
# -------------------------------------------------------------
class CopyrightRegistrationRequest(BaseModel):
    asset_id: str
    certificate_id: str
    registration_number: str
    asset_title: str
    description: Optional[str] = ""
    category: str
    owner_name: str
    owner_email: Optional[str] = ""
    owner_phone: Optional[str] = ""
    owner_address: Optional[str] = ""
    organization: Optional[str] = ""
    country: Optional[str] = ""
    creation_date: Optional[str] = ""
    copyright_type: Optional[str] = ""
    license_type: Optional[str] = ""
    tags: Optional[str] = ""
    notes: Optional[str] = ""
    file_uuid: str
    filename: str
    file_size: int
    sha256_hash: str
    md5_hash: str
    duration: Optional[float] = None
    resolution: Optional[str] = None
    codec: Optional[str] = None
    frame_rate: Optional[float] = None
    bitrate: Optional[int] = None
    audio_channels: Optional[int] = None
    thumbnail_path: Optional[str] = ""
    status: Optional[str] = "Protected"

# -------------------------------------------------------------
# Routes
# -------------------------------------------------------------
@router.post("/upload", status_code=200)
def upload_file(
    file: UploadFile = File(...),
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Phase 1: Handles upload, validates size, and runs dynamic metadata extraction/duplicate checks."""
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    # Read content
    content = file.file.read()
    filesize = len(content)
    if filesize > Config.MAX_ASSET_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum permitted limit of {Config.MAX_ASSET_UPLOAD_SIZE // (1024*1024)}MB."
        )
        
    # Check hashes & duplicate checks
    sha256 = hashlib.sha256(content).hexdigest()
    md5 = hashlib.md5(content).hexdigest()
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT asset_title, asset_id FROM copyright_registrations WHERE sha256_hash = ?;", (sha256,))
        existing = cursor.fetchone()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Duplicate Detected: This file matches registered asset '{existing['asset_title']}' (ID: {existing['asset_id']})."
            )
    finally:
        conn.close()
        
    # Determine category
    mime_type, _ = mimetypes.guess_type(filename)
    if not mime_type:
        mime_type = "application/octet-stream"
        
    category = "Other"
    if mime_type.startswith("video/") or ext in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
        category = "Video"
    elif mime_type.startswith("audio/") or ext in ['.mp3', '.wav', '.aac', '.ogg', '.m4a']:
        category = "Audio"
    elif mime_type.startswith("image/") or ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif', '.svg']:
        category = "Image"
    elif mime_type.startswith("application/pdf") or ext in ['.pdf', '.docx', '.doc', '.txt', '.rtf', '.xlsx']:
        category = "Document"
        
    # Save temporarily
    file_uuid = str(uuid.uuid4())
    temp_filename = f"{file_uuid}{ext}"
    temp_path = os.path.join(TEMP_DIR, temp_filename)
    with open(temp_path, "wb") as f:
        f.write(content)
        
    # Extract metadata using fingerprint.py props
    metadata = {}
    try:
        extracted = extract_file_metadata(temp_path)
        metadata = extracted.get("codec_properties", {})
    except Exception as e:
        print(f"Metadata extraction warning: {e}")
        
    # Generate thumbnail
    thumb_path = generate_thumbnail(temp_path, category, file_uuid)
    
    # Generate temporary credentials
    asset_id = f"TSNC-ASSET-{uuid.uuid4().hex[:8].upper()}"
    certificate_id = f"TSNC-CERT-{uuid.uuid4().hex[:12].upper()}"
    registration_number = f"REG-{uuid.uuid4().hex[:10].upper()}"
    
    # Clean up temp file (or keep it in temp to copy it on final register)
    return {
        "file_uuid": file_uuid,
        "filename": filename,
        "file_size": filesize,
        "sha256_hash": sha256,
        "md5_hash": md5,
        "category": category,
        "thumbnail_path": thumb_path,
        "asset_id": asset_id,
        "certificate_id": certificate_id,
        "registration_number": registration_number,
        "created_timestamp": datetime.utcnow().isoformat() + "Z",
        "metadata": {
            "duration": metadata.get("duration", 0),
            "resolution": f"{metadata.get('width', 0)}x{metadata.get('height', 0)}" if metadata.get('width') else "N/A",
            "codec": metadata.get("codec", "N/A"),
            "frame_rate": metadata.get("fps", 0),
            "bitrate": metadata.get("bitrate", 0),
            "audio_channels": metadata.get("channels", 0),
            "sample_rate": metadata.get("sample_rate", 0),
            "video_format": mime_type if category == "Video" else "N/A",
            "audio_format": mime_type if category == "Audio" else "N/A",
            "creation_date": datetime.fromtimestamp(os.path.getctime(temp_path)).strftime('%Y-%m-%d %H:%M:%S'),
            "last_modified": datetime.fromtimestamp(os.path.getmtime(temp_path)).strftime('%Y-%m-%d %H:%M:%S'),
            "upload_time": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        }
    }

@router.post("/register", status_code=201)
def register_asset(
    req: CopyrightRegistrationRequest,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Saves file to permanent library and stores encrypted copyright data to database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check duplicate hash again to prevent concurrency upload duplicates
        cursor.execute("SELECT id FROM copyright_registrations WHERE sha256_hash = ?;", (req.sha256_hash,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="This file is already registered as a protected asset.")
            
        # Move file from Temp to permanent registrations storage
        ext = os.path.splitext(req.filename)[1].lower()
        temp_path = os.path.join(TEMP_DIR, f"{req.file_uuid}{ext}")
        perm_path = os.path.join(REG_DIR, f"{req.file_uuid}{ext}")
        
        if os.path.exists(temp_path):
            os.rename(temp_path, perm_path)
            
        # Encrypt private fields
        enc_name = encrypt_field(req.owner_name)
        enc_email = encrypt_field(req.owner_email or "")
        enc_phone = encrypt_field(req.owner_phone or "")
        enc_address = encrypt_field(req.owner_address or "")
        
        cursor.execute("""
            INSERT INTO copyright_registrations (
                asset_id, certificate_id, registration_number, status, filename, file_uuid, file_size,
                duration, resolution, codec, frame_rate, bitrate, audio_channels, sha256_hash, md5_hash,
                thumbnail_path, asset_title, description, category, encrypted_owner_name,
                encrypted_owner_email, encrypted_owner_phone, encrypted_owner_address,
                organization, country, creation_date, copyright_type, license_type, tags, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            req.asset_id, req.certificate_id, req.registration_number, req.status, req.filename, req.file_uuid, req.file_size,
            req.duration, req.resolution, req.codec, req.frame_rate, req.bitrate, req.audio_channels, req.sha256_hash, req.md5_hash,
            req.thumbnail_path, req.asset_title, req.description, req.category, enc_name,
            enc_email, enc_phone, enc_address,
            req.organization, req.country, req.creation_date, req.copyright_type, req.license_type, req.tags, req.notes
        ))
        reg_id = cursor.lastrowid
        
        # Log security audit event
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
            VALUES (?, 'REGISTER_COPYRIGHT', 'copyright_registration', ?, ?);
        """, (user["id"], reg_id, f'{{"asset_id": "{req.asset_id}", "asset_title": "{req.asset_title}"}}'))
        
        conn.commit()
        return {"id": reg_id, "asset_id": req.asset_id, "status": req.status}
    finally:
        conn.close()

@router.get("/registrations")
def list_registrations(
    query: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Lists registered copyrights. Decrypts private owner details ONLY for Admins."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        sql = "SELECT * FROM copyright_registrations WHERE 1=1"
        params = []
        
        if category:
            sql += " AND category = ?"
            params.append(category)
        if status:
            sql += " AND status = ?"
            params.append(status)
            
        if query:
            sql += " AND (asset_id LIKE ? OR certificate_id LIKE ? OR filename LIKE ? OR asset_title LIKE ?)"
            like_val = f"%{query}%"
            params.extend([like_val, like_val, like_val, like_val])
            
        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(sql, tuple(params))
        rows = cursor.fetchall()
        
        results = []
        is_admin = user.get("role") == "Admin"
        
        for row in rows:
            r = dict(row)
            # Decrypt or mask private fields
            if is_admin:
                r["owner_name"] = decrypt_field(r["encrypted_owner_name"])
                r["owner_email"] = decrypt_field(r["encrypted_owner_email"])
                r["owner_phone"] = decrypt_field(r["encrypted_owner_phone"])
                r["owner_address"] = decrypt_field(r["encrypted_owner_address"])
            else:
                r["owner_name"] = "[REDACTED]"
                r["owner_email"] = "[REDACTED]"
                r["owner_phone"] = "[REDACTED]"
                r["owner_address"] = "[REDACTED]"
                
            # Remove raw encrypted values from response
            r.pop("encrypted_owner_name", None)
            r.pop("encrypted_owner_email", None)
            r.pop("encrypted_owner_phone", None)
            r.pop("encrypted_owner_address", None)
            
            results.append(r)
            
        return results
    finally:
        conn.close()

@router.get("/registrations/{reg_id}")
def get_registration_details(
    reg_id: int,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves specific copyright record details. Decrypts private details ONLY for Admins."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM copyright_registrations WHERE id = ?;", (reg_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Registration not found.")
            
        r = dict(row)
        is_admin = user.get("role") == "Admin"
        
        if is_admin:
            r["owner_name"] = decrypt_field(r["encrypted_owner_name"])
            r["owner_email"] = decrypt_field(r["encrypted_owner_email"])
            r["owner_phone"] = decrypt_field(r["encrypted_owner_phone"])
            r["owner_address"] = decrypt_field(r["encrypted_owner_address"])
        else:
            r["owner_name"] = "[REDACTED]"
            r["owner_email"] = "[REDACTED]"
            r["owner_phone"] = "[REDACTED]"
            r["owner_address"] = "[REDACTED]"
            
        r.pop("encrypted_owner_name", None)
        r.pop("encrypted_owner_email", None)
        r.pop("encrypted_owner_phone", None)
        r.pop("encrypted_owner_address", None)
        
        return r
    finally:
        conn.close()

@router.put("/registrations/{reg_id}")
def update_registration(
    reg_id: int,
    req: CopyrightRegistrationRequest,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Updates copyright registration details. Admins can update encrypted fields."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM copyright_registrations WHERE id = ?;", (reg_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Registration not found.")
            
        # Encrypt private fields
        enc_name = encrypt_field(req.owner_name)
        enc_email = encrypt_field(req.owner_email or "")
        enc_phone = encrypt_field(req.owner_phone or "")
        enc_address = encrypt_field(req.owner_address or "")
        
        cursor.execute("""
            UPDATE copyright_registrations SET
                asset_title = ?, description = ?, category = ?, status = ?,
                encrypted_owner_name = ?, encrypted_owner_email = ?,
                encrypted_owner_phone = ?, encrypted_owner_address = ?,
                organization = ?, country = ?, creation_date = ?,
                copyright_type = ?, license_type = ?, tags = ?, notes = ?
            WHERE id = ?;
        """, (
            req.asset_title, req.description, req.category, req.status,
            enc_name, enc_email, enc_phone, enc_address,
            req.organization, req.country, req.creation_date,
            req.copyright_type, req.license_type, req.tags, req.notes,
            reg_id
        ))
        
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
            VALUES (?, 'UPDATE_REGISTRATION', 'copyright_registration', ?, ?);
        """, (user["id"], reg_id, f'{{"asset_id": "{req.asset_id}"}}'))
        
        conn.commit()
        return {"status": "success", "detail": "Registration details updated successfully."}
    finally:
        conn.close()

@router.post("/registrations/{reg_id}/archive")
def archive_registration(
    reg_id: int,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Updates registration status to Archived."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id FROM copyright_registrations WHERE id = ?;", (reg_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Registration not found.")
            
        cursor.execute("UPDATE copyright_registrations SET status = 'Archived' WHERE id = ?;", (reg_id,))
        
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
            VALUES (?, 'ARCHIVE_REGISTRATION', 'copyright_registration', ?, '{}');
        """, (user["id"], reg_id))
        
        conn.commit()
        return {"status": "success", "detail": "Registration archived."}
    finally:
        conn.close()

@router.delete("/registrations/{reg_id}")
def delete_registration(
    reg_id: int,
    user: dict = Depends(require_role(["Admin"]))
):
    """Deletes registration permanently from database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT file_uuid, filename, thumbnail_path FROM copyright_registrations WHERE id = ?;", (reg_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Registration not found.")
            
        ext = os.path.splitext(row["filename"])[1].lower()
        file_path = os.path.join(REG_DIR, f"{row['file_uuid']}{ext}")
        thumb_path = os.path.join(PROJECT_ROOT, row["thumbnail_path"]) if row["thumbnail_path"] else ""
        
        # Remove database record
        cursor.execute("DELETE FROM copyright_registrations WHERE id = ?;", (reg_id,))
        
        # Remove files if exist
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        if thumb_path and os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except Exception:
                pass
                
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
            VALUES (?, 'DELETE_REGISTRATION', 'copyright_registration', ?, '{}');
        """, (user["id"], reg_id))
        
        conn.commit()
        return {"status": "success", "detail": "Registration deleted from system."}
    finally:
        conn.close()
