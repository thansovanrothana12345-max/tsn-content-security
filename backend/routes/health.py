import os
from fastapi import APIRouter, HTTPException
from backend.database import get_db_connection
from backend.config import Config

router = APIRouter(prefix="", tags=["Health & Observability"])

def get_dir_size_mb(path: str) -> float:
    total_size = 0
    if not os.path.exists(path):
        return 0.0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                try:
                    total_size += os.path.getsize(fp)
                except OSError:
                    pass
    return round(total_size / (1024 * 1024), 2)

@router.get("/health")
def health_check():
    """Liveness check probe."""
    return {"status": "healthy"}

@router.get("/ready")
def readiness_check():
    """Readiness check probe inspecting db connectivity and accessibility."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1;")
        cursor.fetchone()
        conn.close()
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service Unavailable: Database connection failed: {str(e)}"
        )

@router.get("/metrics")
def metrics():
    """Retrieves operational metrics and disk storage footprints."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # 1. Scan jobs count grouped by status
        cursor.execute("SELECT status, COUNT(*) as count FROM scan_jobs GROUP BY status;")
        scan_jobs_raw = cursor.fetchall()
        scan_jobs_metrics = {status: 0 for status in ["Pending", "Running", "Completed", "Failed", "Cancelled"]}
        for row in scan_jobs_raw:
            scan_jobs_metrics[row["status"]] = row["count"]
            
        # 2. Total assets
        cursor.execute("SELECT COUNT(*) FROM assets WHERE status != 'Deleted';")
        total_assets = cursor.fetchone()[0] or 0
        
        # 3. Total evidence
        cursor.execute("SELECT COUNT(*) FROM evidence;")
        total_evidence = cursor.fetchone()[0] or 0
        
        # 4. Storage directory size
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        storage_path = os.path.join(project_root, Config.STORAGE_DIR)
        size_mb = get_dir_size_mb(storage_path)
        
        return {
            "status": "online",
            "scan_jobs": scan_jobs_metrics,
            "total_assets": total_assets,
            "total_evidence": total_evidence,
            "storage_size_mb": size_mb
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {str(e)}")
    finally:
        conn.close()
