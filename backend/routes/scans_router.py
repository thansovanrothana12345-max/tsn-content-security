import json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from backend.database import get_db_connection
from backend.routes.auth import require_role
from backend.services.url_validator import validate_and_parse_url

router = APIRouter(prefix="/api/v1/scans", tags=["Scans"])

class ScanUrlRequest(BaseModel):
    url: str
    case_id: int | None = None

@router.post("", status_code=202)
def start_scan(
    request: ScanUrlRequest,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer"]))
):
    """Starts an asynchronous scan for a URL."""
    url = request.url.strip()
    validation = validate_and_parse_url(url)
    if not validation["valid"]:
        raise HTTPException(status_code=400, detail={"error": "INVALID_URL", "message": validation["error"]})
        
    platform = validation["platform"]
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # If case_id is provided, verify it exists
        if request.case_id:
            cursor.execute("SELECT id FROM cases WHERE id = ? AND is_deleted = 0;", (request.case_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Target case folder not found.")
                
        # Insert into scan_jobs
        cursor.execute("""
            INSERT INTO scan_jobs (case_id, url, platform, status, progress_percent, created_by)
            VALUES (?, ?, ?, 'Pending', 0.0, ?);
        """, (request.case_id, url, platform, user["id"]))
        job_id = cursor.lastrowid
        
        # Log audit entry
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
            VALUES (?, 'START_SCAN', 'scan_job', ?, ?);
        """, (user["id"], job_id, json.dumps({"url": url, "platform": platform, "case_id": request.case_id})))
        
        conn.commit()
        return {
            "job_id": job_id,
            "url": url,
            "platform": platform,
            "status": "Pending",
            "message": "Scan job successfully queued."
        }
    finally:
        conn.close()

@router.get("/{job_id}/status")
def get_scan_status(
    job_id: int,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves status and progress percentage of a scan job."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, url, platform, status, progress_percent, error_message FROM scan_jobs WHERE id = ?;", (job_id,))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Scan job not found.")
        return dict(row)
    finally:
        conn.close()

@router.get("/results")
def list_scan_results(
    job_id: int | None = None,
    platform: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort_by: str = "created_at",
    order: str = "DESC",
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Lists parsed scan results with pagination, sorting, and platform filtering."""
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    
    allowed_sort = ["id", "job_id", "url", "platform", "title", "uploader", "upload_date", "created_at"]
    if sort_by not in allowed_sort:
        sort_by = "created_at"
        
    order_upper = order.upper()
    if order_upper not in ["ASC", "DESC"]:
        order_upper = "DESC"
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        query = "SELECT * FROM scan_results WHERE 1=1"
        params = []
        
        if job_id is not None:
            query += " AND job_id = ?"
            params.append(job_id)
        if platform:
            query += " AND platform = ?"
            params.append(platform)
            
        query += f" ORDER BY {sort_by} {order_upper} LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()
