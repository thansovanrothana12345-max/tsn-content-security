import os
import uuid
import hashlib
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form
from pydantic import BaseModel
from backend.database import get_db_connection
from backend.routes.auth import require_role
from backend.config import Config

router = APIRouter(prefix="/api/v1/assets", tags=["Assets"])

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS_DIR = os.path.join(PROJECT_ROOT, Config.STORAGE_DIR, "originals")

class AssetUpdateStatusRequest(BaseModel):
    status: str

@router.post("", status_code=201)
def upload_asset(
    case_id: int = Form(None),
    asset_type: str = Form(...),
    file: UploadFile = File(...),
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Ingests a new registered brand asset into the Asset Library."""
    if asset_type not in ['Video', 'Image', 'Audio', 'Document', 'Logo', 'Trademark']:
        raise HTTPException(status_code=400, detail="Invalid asset type.")
        
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()
    
    # Read file content & validate size
    content = file.file.read()
    filesize = len(content)
    if filesize > Config.MAX_ASSET_UPLOAD_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Asset file size exceeds maximum permitted limit of {Config.MAX_ASSET_UPLOAD_SIZE // (1024*1024)}MB."
        )
        
    sha256_hash = hashlib.sha256(content).hexdigest()
    
    # Generate unique ID
    file_uuid = str(uuid.uuid4())
    unique_filename = f"{file_uuid}{ext}"
    os.makedirs(ASSETS_DIR, exist_ok=True)
    target_path = os.path.join(ASSETS_DIR, unique_filename)
    
    with open(target_path, "wb") as f:
        f.write(content)
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check duplicate hash
        cursor.execute("SELECT id FROM assets WHERE sha256_hash = ?;", (sha256_hash,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Asset with this file hash already exists.")
            
        # Verify case if provided
        if case_id:
            cursor.execute("SELECT id FROM cases WHERE id = ? AND is_deleted = 0;", (case_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Target case folder not found.")
                
        cursor.execute("""
            INSERT INTO assets (case_id, asset_type, filename, file_uuid, sha256_hash, owner_user_id, status, fingerprint_status)
            VALUES (?, ?, ?, ?, ?, ?, 'Active', 'Pending');
        """, (case_id, asset_type, filename, file_uuid, sha256_hash, user["id"]))
        asset_id = cursor.lastrowid
        
        # Log audit entry
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
            VALUES (?, 'INGEST_ASSET', 'asset', ?, ?);
        """, (user["id"], asset_id, f'{{"filename": "{filename}", "asset_type": "{asset_type}"}}'))
        
        conn.commit()
        return {
            "id": asset_id,
            "case_id": case_id,
            "asset_type": asset_type,
            "filename": filename,
            "file_uuid": file_uuid,
            "sha256_hash": sha256_hash,
            "owner": user["username"],
            "status": "Active",
            "fingerprint_status": "Pending"
        }
    finally:
        conn.close()

@router.get("")
def list_assets(
    case_id: int = None,
    asset_type: str = None,
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "upload_date",
    order: str = "DESC",
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves all registered assets filtered by case, type, or status with pagination and sorting."""
    # Input validation
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    
    allowed_sort = ["id", "case_id", "asset_type", "filename", "upload_date", "status", "fingerprint_status"]
    if sort_by not in allowed_sort:
        sort_by = "upload_date"
        
    order_upper = order.upper()
    if order_upper not in ["ASC", "DESC"]:
        order_upper = "DESC"
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM assets WHERE status != 'Deleted'"
        params = []
        
        if case_id is not None:
            query += " AND case_id = ?"
            params.append(case_id)
        if asset_type:
            query += " AND asset_type = ?"
            params.append(asset_type)
        if status:
            query += " AND status = ?"
            params.append(status)
            
        # Append safe sorting and pagination
        query += f" ORDER BY {sort_by} {order_upper} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.get("/{asset_id}")
def get_asset_details(
    asset_id: int,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves detailed parameters of a registered asset."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM assets WHERE id = ?;", (asset_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Asset not found.")
        return dict(row)
    finally:
        conn.close()
