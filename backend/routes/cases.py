from fastapi import APIRouter, HTTPException, Depends, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, constr
from typing import Optional, Literal
import json
import time
import io
import zipfile
import os
from backend.database import get_db_connection
from backend.routes.auth import require_role

router = APIRouter(prefix="/api/v1/cases", tags=["Cases"])

class CaseCreate(BaseModel):
    title: constr(min_length=1, max_length=100)
    client_name: constr(min_length=1, max_length=100)
    platform: constr(min_length=1, max_length=100)
    priority: Literal["Critical", "High", "Medium", "Low"] = "Medium"
    description: Optional[str] = None
    assigned_user_id: Optional[int] = None
    tags: Optional[str] = None

class CaseUpdate(BaseModel):
    title: Optional[constr(min_length=1, max_length=100)] = None
    client_name: Optional[constr(min_length=1, max_length=100)] = None
    platform: Optional[constr(min_length=1, max_length=100)] = None
    priority: Optional[Literal["Critical", "High", "Medium", "Low"]] = None
    description: Optional[str] = None
    assigned_user_id: Optional[int] = None
    status: Optional[Literal["Draft", "Investigating", "Scanning", "Evidence Collected", "Verified", "DMCA Draft", "DMCA Sent", "Resolved", "Archived", "Active", "Closed", "Suspended"]] = None
    tags: Optional[str] = None

def validate_user_exists(cursor, user_id: int):
    if user_id is None:
         return
    cursor.execute("SELECT id FROM users WHERE id = ?;", (user_id,))
    if not cursor.fetchone():
         raise HTTPException(status_code=400, detail=f"User with ID {user_id} does not exist.")

@router.get("")
def list_cases(
    response: Response,
    q: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    platform: Optional[str] = None,
    owner_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    sort_by: Optional[str] = "newest",
    page: Optional[int] = None,
    limit: Optional[int] = None,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Lists all cases with search query, filters, dynamic sorting and soft-delete filtering."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        where_clauses = ["c.is_deleted = 0"]
        params = []
        
        if q and len(q.strip()) > 0:
            search_pattern = f"%{q.strip()}%"
            if q.strip().isdigit():
                where_clauses.append("(c.id = ? OR c.title LIKE ? OR c.client_name LIKE ? OR c.platform LIKE ? OR u_owner.username LIKE ? OR u_assignee.username LIKE ? OR c.tags LIKE ?)")
                params.extend([int(q.strip()), search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, search_pattern])
            else:
                where_clauses.append("(c.title LIKE ? OR c.client_name LIKE ? OR c.platform LIKE ? OR u_owner.username LIKE ? OR u_assignee.username LIKE ? OR c.tags LIKE ?)")
                params.extend([search_pattern, search_pattern, search_pattern, search_pattern, search_pattern, search_pattern])
                
        if status:
            where_clauses.append("c.status = ?")
            params.append(status)
            
        if priority:
            where_clauses.append("c.priority = ?")
            params.append(priority)
            
        if platform:
            where_clauses.append("c.platform = ?")
            params.append(platform)
            
        if owner_id:
            where_clauses.append("(c.owner_user_id = ? OR c.assigned_user_id = ?)")
            params.extend([owner_id, owner_id])
            
        if start_date:
            where_clauses.append("c.created_at >= ?")
            params.append(start_date)
            
        if end_date:
            where_clauses.append("c.created_at <= ?")
            params.append(end_date)
            
        order_clause = "c.created_at DESC"
        if sort_by == "oldest":
            order_clause = "c.created_at ASC"
        elif sort_by == "alphabetical":
            order_clause = "c.title ASC"
        elif sort_by == "priority":
            order_clause = "CASE c.priority WHEN 'Critical' THEN 1 WHEN 'High' THEN 2 WHEN 'Medium' THEN 3 WHEN 'Low' THEN 4 ELSE 5 END ASC, c.created_at DESC"
        elif sort_by == "status":
            order_clause = "CASE c.status WHEN 'Draft' THEN 1 WHEN 'Investigating' THEN 2 WHEN 'Scanning' THEN 3 WHEN 'Evidence Collected' THEN 4 WHEN 'Verified' THEN 5 WHEN 'DMCA Draft' THEN 6 WHEN 'DMCA Sent' THEN 7 WHEN 'Resolved' THEN 8 WHEN 'Archived' THEN 9 ELSE 10 END ASC, c.created_at DESC"
        elif sort_by == "evidence_count":
            order_clause = "evidence_count DESC, c.created_at DESC"
            
        where_str = " AND ".join(where_clauses)
        query = f"""
        SELECT c.*, 
               u_owner.username as owner_username,
               u_assignee.username as assignee_username,
               vr.status as verification_status,
               (SELECT COUNT(*) FROM originals WHERE case_id = c.id) as originals_count,
               (SELECT COUNT(*) FROM evidence WHERE case_id = c.id) as evidence_count,
               (SELECT COUNT(*) FROM evidence WHERE case_id = c.id AND similarity_score >= 0.8) as matches_count
        FROM cases c
        LEFT JOIN users u_owner ON c.owner_user_id = u_owner.id
        LEFT JOIN users u_assignee ON c.assigned_user_id = u_assignee.id
        LEFT JOIN verification_records vr ON vr.case_id = c.id
        WHERE {where_str}
        ORDER BY {order_clause};
        """
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
    finally:
        conn.close()
    
    total_count = len(rows)
    response.headers["X-Total-Count"] = str(total_count)
    
    results = [dict(row) for row in rows]
    if page and limit:
        start = (page - 1) * limit
        end = start + limit
        return results[start:end]
        
    return results

@router.post("", status_code=201)
def create_case(case: CaseCreate, user: dict = Depends(require_role(["Admin", "Editor"]))):
    """Creates a new copyright case with owner assignments."""
    if case.priority not in ["Critical", "High", "Medium", "Low"]:
         raise HTTPException(status_code=400, detail="Invalid priority level.")
         
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        validate_user_exists(cursor, case.assigned_user_id)
        
        cursor.execute("""
            INSERT INTO cases (title, description, owner_user_id, assigned_user_id, priority, status, tags, client_name, platform)
            VALUES (?, ?, ?, ?, ?, 'Draft', ?, ?, ?);
        """, (case.title, case.description, user["id"], case.assigned_user_id, case.priority, case.tags, case.client_name, case.platform))
        
        case_id = cursor.lastrowid
        
        details = json.dumps({
             "title": case.title,
             "priority": case.priority,
             "owner_user_id": user["id"],
             "assigned_user_id": case.assigned_user_id,
             "tags": case.tags,
             "client_name": case.client_name,
             "platform": case.platform
        })
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
            VALUES (?, 'CREATE_CASE', 'case', ?, ?)
        """, (user["id"], case_id, details))
        
        conn.commit()
        
        cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        new_case = cursor.fetchone()
        return dict(new_case)
    finally:
        conn.close()

@router.get("/{case_id}")
def get_case(case_id: int, user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))):
    """Retrieves detailed parameters of a single case."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
             SELECT c.*, 
                    u_owner.username as owner_username, 
                    u_assignee.username as assignee_username
             FROM cases c
             LEFT JOIN users u_owner ON c.owner_user_id = u_owner.id
             LEFT JOIN users u_assignee ON c.assigned_user_id = u_assignee.id
             WHERE c.id = ?;
        """, (case_id,))
        row = cursor.fetchone()
    finally:
        conn.close()
    
    if not row:
        raise HTTPException(
            status_code=404, 
            detail={"error": "NOT_FOUND", "message": "The requested case folder does not exist."}
        )
    return dict(row)

@router.put("/{case_id}")
def update_case(case_id: int, case: CaseUpdate, user: dict = Depends(require_role(["Admin", "Editor"]))):
    """Updates case properties (status transitions, assignment changes, tags)."""
    if case.status and case.status not in ["Draft", "Investigating", "Scanning", "Evidence Collected", "Verified", "DMCA Draft", "DMCA Sent", "Resolved", "Archived", "Active", "Closed", "Suspended"]:
        raise HTTPException(status_code=400, detail="Invalid case status workflow state.")
    if case.priority and case.priority not in ["Critical", "High", "Medium", "Low"]:
         raise HTTPException(status_code=400, detail="Invalid priority level.")
         
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="The requested case folder does not exist.")
            
        validate_user_exists(cursor, case.assigned_user_id)
        
        existing_dict = dict(existing)
        update_fields = []
        params = []
        changes = {}
        
        if case.title is not None:
            update_fields.append("title = ?")
            params.append(case.title)
            changes["title"] = {"old": existing_dict.get("title"), "new": case.title}
            
        if case.client_name is not None:
            update_fields.append("client_name = ?")
            params.append(case.client_name)
            changes["client_name"] = {"old": existing_dict.get("client_name"), "new": case.client_name}
            
        if case.platform is not None:
            update_fields.append("platform = ?")
            params.append(case.platform)
            changes["platform"] = {"old": existing_dict.get("platform"), "new": case.platform}
            
        if case.description is not None:
            update_fields.append("description = ?")
            params.append(case.description)
            changes["description"] = {"old": existing_dict.get("description"), "new": case.description}
            
        if case.priority is not None:
             update_fields.append("priority = ?")
             params.append(case.priority)
             changes["priority"] = {"old": existing_dict.get("priority"), "new": case.priority}
             
        if case.status is not None:
            update_fields.append("status = ?")
            params.append(case.status)
            changes["status"] = {"old": existing_dict.get("status"), "new": case.status}
            
        if case.assigned_user_id is not None:
             update_fields.append("assigned_user_id = ?")
             params.append(case.assigned_user_id)
             changes["assigned_user_id"] = {"old": existing_dict.get("assigned_user_id"), "new": case.assigned_user_id}
             
        if case.tags is not None:
             update_fields.append("tags = ?")
             params.append(case.tags)
             changes["tags"] = {"old": existing_dict.get("tags"), "new": case.tags}
             
        if not update_fields:
            return dict(existing)
            
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        params.append(case_id)
        query = f"UPDATE cases SET {', '.join(update_fields)} WHERE id = ?"
        cursor.execute(query, tuple(params))
        
        # Audit log
        details = json.dumps(changes)
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
            VALUES (?, 'UPDATE_CASE', 'case', ?, ?)
        """, (user["id"], case_id, details))
        
        conn.commit()
        
        cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        updated_case = cursor.fetchone()
        return dict(updated_case)
    finally:
        conn.close()

@router.delete("/{case_id}")
def delete_case(case_id: int, user: dict = Depends(require_role(["Admin"]))):
    """Soft deletes a case by setting is_deleted = 1."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
        existing = cursor.fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="The requested case folder does not exist.")
            
        cursor.execute("UPDATE cases SET is_deleted = 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (case_id,))
        
        details = json.dumps({"title": existing["title"]})
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
            VALUES (?, 'DELETE_CASE', 'case', ?, ?)
        """, (user["id"], case_id, details))
        
        conn.commit()
    finally:
        conn.close()
    return {"message": f"Case {case_id} deleted successfully."}

@router.get("/{case_id}/timeline")
def get_case_timeline(
    case_id: int, 
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves a unified chronological history timeline of creation, updates, notes, and activity for a case."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id, title, created_at FROM cases WHERE id = ? AND is_deleted = 0;", (case_id,))
        case = cursor.fetchone()
        if not case:
            raise HTTPException(status_code=404, detail="The requested case folder does not exist.")
            
        timeline = []
        
        # 1. Creation Event
        timeline.append({
            "type": "Created",
            "timestamp": case["created_at"],
            "username": "System",
            "details": f"Case folder '{case['title']}' was initialized."
        })
        
        # 2. Update log history
        cursor.execute("""
            SELECT a.action, a.details_json, a.created_at, u.username
            FROM audit_logs a
            LEFT JOIN users u ON a.user_id = u.id
            WHERE a.entity_type = 'case' AND a.entity_id = ?
            ORDER BY a.created_at ASC;
        """, (case_id,))
        logs = cursor.fetchall()
        for log in logs:
            if log["action"] == "CREATE_CASE":
                continue
                
            details_text = ""
            if log["action"] == "UPDATE_CASE" and log["details_json"]:
                try:
                    changes = json.loads(log["details_json"])
                    details_list = []
                    for field, val in changes.items():
                        details_list.append(f"Changed {field} from '{val.get('old')}' to '{val.get('new')}'")
                    details_text = ", ".join(details_list)
                except Exception:
                    details_text = f"Audit log parse failed: {log['details_json']}"
            else:
                details_text = f"Action: {log['action']}"
                
            timeline.append({
                "type": "History",
                "timestamp": log["created_at"],
                "username": log["username"] or "System Admin",
                "details": details_text
            })
            
        # 3. Custom Review Notes
        cursor.execute("""
            SELECT n.note, n.created_at, u.username
            FROM case_notes n
            LEFT JOIN users u ON n.user_id = u.id
            WHERE n.case_id = ?
            ORDER BY n.created_at ASC;
        """, (case_id,))
        notes = cursor.fetchall()
        for note in notes:
            timeline.append({
                "type": "Note",
                "timestamp": note["created_at"],
                "username": note["username"] or "Reviewer",
                "details": note["note"]
            })
    finally:
        conn.close()
        
    timeline.sort(key=lambda x: x["timestamp"])
    return timeline

class NoteCreate(BaseModel):
    note: constr(min_length=1)

@router.get("/search")
def search_cases(
    q: str,
    response: Response,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Searches cases fuzzy matching title, description, or tags by delegating to list_cases."""
    if not q or len(q.strip()) == 0:
         raise HTTPException(status_code=400, detail="Search query parameter 'q' must not be empty.")
         
    return list_cases(response=response, q=q, user=user)

@router.post("/{case_id}/notes", status_code=201)
def create_case_note(
    case_id: int,
    payload: NoteCreate,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer"]))
):
    """Adds a text note annotation remark linked to a case."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM cases WHERE id = ?;", (case_id,))
        if not cursor.fetchone():
             raise HTTPException(status_code=404, detail="Parent case folder not found.")
             
        clean_note = payload.note.replace("<script>", "").replace("</script>", "")
        
        cursor.execute("""
             INSERT INTO case_notes (case_id, user_id, note)
             VALUES (?, ?, ?);
        """, (case_id, user["id"], clean_note))
        note_id = cursor.lastrowid
        
        details = json.dumps({"note_preview": clean_note[:30]})
        cursor.execute("""
             INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
             VALUES (?, 'CREATE_NOTE', 'note', ?, ?);
        """, (user["id"], note_id, details))
        
        conn.commit()
        
        cursor.execute("""
             SELECT n.*, u.username 
             FROM case_notes n
             JOIN users u ON n.user_id = u.id
             WHERE n.id = ?;
        """, (note_id,))
        new_note = cursor.fetchone()
        return dict(new_note)
    finally:
        conn.close()

@router.get("/{case_id}/notes")
def list_case_notes(
    case_id: int,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves chronological case notes annotation logs."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM cases WHERE id = ?;", (case_id,))
        if not cursor.fetchone():
             raise HTTPException(status_code=404, detail="Parent case folder not found.")
             
        cursor.execute("""
             SELECT n.id, n.case_id, n.user_id, n.note, n.created_at, u.username
             FROM case_notes n
             JOIN users u ON n.user_id = u.id
             WHERE n.case_id = ?
             ORDER BY n.created_at ASC;
        """, (case_id,))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

@router.get("/{case_id}/export")
def export_case_package(
    case_id: int,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Compiles complete case data history and streams a ZIP file archive."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM cases WHERE id = ?;", (case_id,))
        case_row = cursor.fetchone()
        if not case_row:
             raise HTTPException(status_code=404, detail="Case folder not found.")
             
        case_dict = dict(case_row)
        
        cursor.execute("SELECT * FROM case_notes WHERE case_id = ? ORDER BY created_at ASC;", (case_id,))
        notes_rows = cursor.fetchall()
        notes_list = [dict(n) for n in notes_rows]
        
        cursor.execute("SELECT * FROM timeline_events WHERE case_id = ? ORDER BY timestamp ASC;", (case_id,))
        timeline_rows = cursor.fetchall()
        timeline_list = [dict(t) for t in timeline_rows]
        
        cursor.execute("""
             SELECT a.id, a.filename, a.filepath, a.filesize 
             FROM evidence_attachments a
             JOIN evidence e ON a.evidence_id = e.id
             WHERE e.case_id = ?;
        """, (case_id,))
        attachments_rows = cursor.fetchall()
        attachments_list = [dict(a) for a in attachments_rows]
        
        cursor.execute("SELECT id, title, screenshot_path FROM evidence WHERE case_id = ?;", (case_id,))
        evidence_rows = cursor.fetchall()
        evidence_list = [dict(ev) for ev in evidence_rows]
        
        root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
             zip_file.writestr("case_metadata.json", json.dumps(case_dict, default=str, indent=4))
             zip_file.writestr("notes.json", json.dumps(notes_list, default=str, indent=4))
             zip_file.writestr("timeline.json", json.dumps(timeline_list, default=str, indent=4))
             
             for attach in attachments_list:
                  filepath = attach["filepath"]
                  if os.path.exists(filepath):
                       if os.path.abspath(filepath).startswith(os.path.abspath(os.path.join(root_dir, "storage"))):
                            zip_file.write(filepath, arcname=f"attachments/{attach['filename']}")
                            
             for ev in evidence_list:
                  sp = ev["screenshot_path"]
                  if sp:
                       fn = os.path.basename(sp)
                       filepath = os.path.join(root_dir, "storage", "evidence", fn)
                       if os.path.exists(filepath):
                            zip_file.write(filepath, arcname=f"evidence/{fn}")
                            
        zip_data = zip_buffer.getvalue()
    finally:
        conn.close()
        
    zip_buffer.seek(0)
    headers = {
         "Content-Disposition": f"attachment; filename=case_{case_id}_export.zip"
    }
    return StreamingResponse(iter([zip_data]), media_type="application/zip", headers=headers)

@router.post("/{case_id}/archive", status_code=200)
def archive_case_folder(
    case_id: int,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Archiving case by setting status to Archived and registering an audit log entry."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT title FROM cases WHERE id = ? AND is_deleted = 0;", (case_id,))
        case_row = cursor.fetchone()
        if not case_row:
             raise HTTPException(status_code=404, detail="Case folder not found.")
             
        cursor.execute("UPDATE cases SET status = 'Archived', updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (case_id,))
        
        # Audit log
        details = json.dumps({"title": case_row["title"], "action": "archive"})
        cursor.execute("""
             INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
             VALUES (?, 'ARCHIVE_CASE', 'case', ?, ?);
        """, (user["id"], case_id, details))
        
        conn.commit()
    finally:
        conn.close()
        
    return {"message": f"Case #{case_id} successfully archived."}

@router.post("/{case_id}/duplicate", status_code=201)
def duplicate_case(
    case_id: int,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Duplicates a case metadata and registers audit log entry."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM cases WHERE id = ? AND is_deleted = 0;", (case_id,))
        orig = cursor.fetchone()
        if not orig:
            raise HTTPException(status_code=404, detail="Case not found.")
            
        orig_dict = dict(orig)
        new_title = f"Copy of {orig_dict['title']}"
        if len(new_title) > 100:
            new_title = new_title[:100]
            
        cursor.execute("""
            INSERT INTO cases (title, description, owner_user_id, assigned_user_id, priority, status, tags, client_name, platform)
            VALUES (?, ?, ?, ?, ?, 'Draft', ?, ?, ?);
        """, (new_title, orig_dict["description"], user["id"], orig_dict["assigned_user_id"], orig_dict["priority"], orig_dict["tags"], orig_dict["client_name"], orig_dict["platform"]))
        
        new_id = cursor.lastrowid
        
        # Audit log
        details = json.dumps({"original_case_id": case_id, "new_case_id": new_id, "title": new_title})
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
            VALUES (?, 'DUPLICATE_CASE', 'case', ?, ?)
        """, (user["id"], new_id, details))
        
        conn.commit()
        
        cursor.execute("SELECT * FROM cases WHERE id = ?;", (new_id,))
        new_case = cursor.fetchone()
        return dict(new_case)
    finally:
        conn.close()


