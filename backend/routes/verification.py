from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Literal
import json
from datetime import datetime
from backend.database import get_db_connection
from backend.routes.auth import require_role

router = APIRouter(prefix="/api/v1/verification", tags=["Verification"])

class VerificationCreate(BaseModel):
    case_id: int
    status: Optional[Literal["Verified", "Pending", "Rejected"]] = "Pending"
    ai_score: Optional[float] = 0.0
    reviewer_id: Optional[int] = None
    metadata_validation: Optional[Literal["Verified", "Warning", "Pending", "Failed"]] = "Pending"
    hash_verification: Optional[Literal["Verified", "Warning", "Pending", "Failed"]] = "Pending"
    evidence_summary: Optional[str] = ""

class VerificationUpdate(BaseModel):
    status: Optional[Literal["Verified", "Pending", "Rejected"]] = None
    ai_score: Optional[float] = None
    reviewer_id: Optional[int] = None
    metadata_validation: Optional[Literal["Verified", "Warning", "Pending", "Failed"]] = None
    hash_verification: Optional[Literal["Verified", "Warning", "Pending", "Failed"]] = None
    evidence_summary: Optional[str] = None
    reviewer_notes: Optional[str] = None

@router.get("")
def list_verifications(user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))):
    """Retrieves all verification records with joined case details, evidence summaries, and notes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Refresh/Sync verification records for any new cases that might have been created without one
    try:
        cursor.execute("""
        INSERT OR IGNORE INTO verification_records (case_id, status, ai_score, reviewer_id, metadata_validation, hash_verification, evidence_summary)
        SELECT 
            c.id, 
            'Pending', 
            COALESCE((SELECT MAX(similarity_score) FROM evidence WHERE case_id = c.id), 0.0),
            (SELECT id FROM users WHERE role = 'Admin' LIMIT 1),
            'Pending',
            'Pending',
            'Pending initial evaluation of evidence files.'
        FROM cases c;
        """)
        conn.commit()
    except Exception as e:
        pass
        
    query = """
    SELECT vr.*, 
           c.title as case_name,
           u_owner.username as owner_username,
           u_reviewer.username as reviewer_username,
           (SELECT COUNT(*) FROM evidence WHERE case_id = c.id) as evidence_count,
           (SELECT json_group_array(json_object('id', id, 'platform', platform, 'url', url, 'title', title, 'uploader', uploader, 'similarity_score', similarity_score, 'status', status)) FROM evidence WHERE case_id = c.id) as evidence_files_json,
           (SELECT json_group_array(json_object('id', id, 'filename', filename, 'filepath', filepath, 'filesize', filesize)) FROM evidence_attachments WHERE evidence_id IN (SELECT id FROM evidence WHERE case_id = c.id)) as evidence_attachments_json,
           (SELECT json_group_array(json_object('id', id, 'filename', filename, 'filesize', filesize)) FROM originals WHERE case_id = c.id) as originals_json,
           (SELECT json_group_array(json_object('id', vn.id, 'note', vn.note, 'username', u_note.username, 'created_at', vn.created_at)) 
            FROM verification_notes vn 
            JOIN users u_note ON vn.user_id = u_note.id 
            WHERE vn.verification_id = vr.id 
            ORDER BY vn.created_at DESC) as notes_json
    FROM verification_records vr
    JOIN cases c ON vr.case_id = c.id
    LEFT JOIN users u_owner ON c.owner_user_id = u_owner.id
    LEFT JOIN users u_reviewer ON vr.reviewer_id = u_reviewer.id
    ORDER BY vr.updated_at DESC;
    """
    
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        
        result = []
        for row in rows:
            d = dict(row)
            # Parse JSON fields
            d["evidence_files"] = json.loads(d["evidence_files_json"]) if d["evidence_files_json"] else []
            d["evidence_attachments"] = json.loads(d["evidence_attachments_json"]) if d["evidence_attachments_json"] else []
            d["originals"] = json.loads(d["originals_json"]) if d["originals_json"] else []
            d["notes"] = json.loads(d["notes_json"]) if d["notes_json"] else []
            
            # Clean up temporary JSON columns from output dict
            del d["evidence_files_json"]
            del d["evidence_attachments_json"]
            del d["originals_json"]
            del d["notes_json"]
            result.append(d)
            
        conn.close()
        return result
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Database query error: {str(e)}")

@router.post("", status_code=201)
def create_verification(data: VerificationCreate, user: dict = Depends(require_role(["Admin", "Editor"]))):
    """Creates a new verification record manually."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if case exists
    cursor.execute("SELECT id FROM cases WHERE id = ?;", (data.case_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Target case does not exist.")
        
    # Check if already exists
    cursor.execute("SELECT id FROM verification_records WHERE case_id = ?;", (data.case_id,))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=400, detail="Verification record already exists for this case.")
        
    try:
        cursor.execute("""
        INSERT INTO verification_records (case_id, status, ai_score, reviewer_id, metadata_validation, hash_verification, evidence_summary)
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (data.case_id, data.status, data.ai_score, data.reviewer_id, data.metadata_validation, data.hash_verification, data.evidence_summary))
        rec_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {"id": rec_id, "message": "Verification record initialized successfully."}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{id}")
def update_verification(id: int, data: VerificationUpdate, user: dict = Depends(require_role(["Admin", "Editor", "Reviewer"]))):
    """Updates verification record details, metadata validations, status, and appends reviewer notes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM verification_records WHERE id = ?;", (id,))
    rec = cursor.fetchone()
    if not rec:
        conn.close()
        raise HTTPException(status_code=404, detail="Verification record not found.")
        
    try:
        # Build dynamic update fields
        fields = []
        params = []
        
        if data.status is not None:
            fields.append("status = ?")
            params.append(data.status)
        if data.ai_score is not None:
            fields.append("ai_score = ?")
            params.append(data.ai_score)
        if data.reviewer_id is not None:
            fields.append("reviewer_id = ?")
            params.append(data.reviewer_id)
        if data.metadata_validation is not None:
            fields.append("metadata_validation = ?")
            params.append(data.metadata_validation)
        if data.hash_verification is not None:
            fields.append("hash_verification = ?")
            params.append(data.hash_verification)
        if data.evidence_summary is not None:
            fields.append("evidence_summary = ?")
            params.append(data.evidence_summary)
            
        if fields:
            fields.append("updated_at = CURRENT_TIMESTAMP")
            query = f"UPDATE verification_records SET {', '.join(fields)} WHERE id = ?;"
            params.append(id)
            cursor.execute(query, tuple(params))
            
        # Append reviewer note if provided
        if data.reviewer_notes and len(data.reviewer_notes.strip()) > 0:
            cursor.execute("""
            INSERT INTO verification_notes (verification_id, user_id, note)
            VALUES (?, ?, ?);
            """, (id, user["id"], data.reviewer_notes))
            
        conn.commit()
        conn.close()
        return {"id": id, "message": "Verification record updated successfully."}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{id}")
def delete_verification(id: int, user: dict = Depends(require_role(["Admin"]))):
    """Deletes a verification record (Admin only)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM verification_records WHERE id = ?;", (id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Verification record not found.")
        
    try:
        cursor.execute("DELETE FROM verification_records WHERE id = ?;", (id,))
        conn.commit()
        conn.close()
        return {"message": "Verification record deleted successfully."}
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=str(e))
