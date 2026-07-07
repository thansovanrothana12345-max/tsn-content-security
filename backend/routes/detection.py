from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional
from backend.routes.auth import get_current_user
from backend.models.detection_result import DetectionResult
from backend.services.detection_service import DetectionService
from backend.database import get_db_connection

router = APIRouter(prefix="/api/v1/detection", tags=["AI Detection Operations"])

class DetectionCheckRequest(BaseModel):
    case_id: int
    evidence_id: int
    asset_file: str

@router.post("/check", response_model=DetectionResult, status_code=status.HTTP_200_OK)
def trigger_detection_check(
    req: DetectionCheckRequest,
    user: dict = Depends(get_current_user)
):
    """Triggers an on-demand multi-modal AI detection check for an evidence asset."""
    try:
        service = DetectionService()
        result_dict = service.run_detection_check(
            case_id=req.case_id,
            evidence_id=req.evidence_id,
            asset_file=req.asset_file
        )
        return result_dict
    except FileNotFoundError as fnf_err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(fnf_err)
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Detection engine exception: {str(err)}"
        )

@router.get("/status/{job_id}", status_code=status.HTTP_200_OK)
def get_detection_job_status(
    job_id: int,
    user: dict = Depends(get_current_user)
):
    """Checks the current background processing state and progress percentage of a scan job."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, progress_percent, error_message FROM scan_jobs WHERE id = ?;", (job_id,))
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scan job not found with ID: {job_id}"
        )
        
    status_str = row[0] if isinstance(row, (tuple, list)) else row["status"]
    progress = row[1] if isinstance(row, (tuple, list)) else row["progress_percent"]
    error_msg = row[2] if isinstance(row, (tuple, list)) else row["error_message"]
    
    return {
        "job_id": job_id,
        "status": status_str,
        "progress_percent": progress,
        "error_message": error_msg
    }
