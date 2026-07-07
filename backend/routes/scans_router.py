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


class CreateSessionRequest(BaseModel):
    case_id: int

@router.post("/sessions", status_code=201)
def start_scan_session(
    request: CreateSessionRequest,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Creates a new scan session with a template DAG of tasks."""
    from backend.services.scan_orchestrator import ScanOrchestrator
    try:
        session_data = ScanOrchestrator.create_session(request.case_id, user["id"])
        return session_data
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@router.get("/sessions/{session_uuid}/progress")
def get_session_progress_api(
    session_uuid: str,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves real-time progress details of a scan session."""
    from backend.services.scan_orchestrator import ScanOrchestrator
    try:
        progress_data = ScanOrchestrator.get_session_progress(session_uuid)
        return progress_data
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@router.post("/sessions/{session_uuid}/pause")
def pause_session_api(
    session_uuid: str,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Pauses a running scan session."""
    from backend.services.scan_orchestrator import ScanOrchestrator
    try:
        success = ScanOrchestrator.pause_session(session_uuid)
        if not success:
            raise HTTPException(status_code=400, detail="Session cannot be paused (must be in Pending or Running state).")
        return {"message": "Scan session successfully paused."}
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@router.post("/sessions/{session_uuid}/resume")
def resume_session_api(
    session_uuid: str,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Resumes a paused scan session."""
    from backend.services.scan_orchestrator import ScanOrchestrator
    try:
        success = ScanOrchestrator.resume_session(session_uuid)
        if not success:
            raise HTTPException(status_code=400, detail="Session cannot be resumed (must be in Paused state).")
        return {"message": "Scan session successfully resumed."}
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@router.post("/sessions/{session_uuid}/cancel")
def cancel_session_api(
    session_uuid: str,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Cancels a scan session."""
    from backend.services.scan_orchestrator import ScanOrchestrator
    try:
        success = ScanOrchestrator.cancel_session(session_uuid)
        if not success:
            raise HTTPException(status_code=400, detail="Session cannot be cancelled.")
        return {"message": "Scan session successfully cancelled."}
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@router.post("/sessions/{session_uuid}/retry")
def retry_session_api(
    session_uuid: str,
    user: dict = Depends(require_role(["Admin", "Editor"]))
):
    """Retries a failed or cancelled scan session."""
    from backend.services.scan_orchestrator import ScanOrchestrator
    try:
        success = ScanOrchestrator.retry_session(session_uuid)
        if not success:
            raise HTTPException(status_code=400, detail="Session cannot be retried.")
        return {"message": "Scan session successfully reset to Pending for retry."}
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))

@router.get("/sessions/{session_uuid}/timeline")
def get_session_timeline_api(
    session_uuid: str,
    user: dict = Depends(require_role(["Admin", "Editor", "Reviewer", "Guest"]))
):
    """Retrieves chronological timeline logs for a scan session."""
    from backend.services.scan_orchestrator import ScanOrchestrator
    try:
        timeline = ScanOrchestrator.get_session_timeline(session_uuid)
        return timeline
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as err:
        raise HTTPException(status_code=500, detail=str(err))
