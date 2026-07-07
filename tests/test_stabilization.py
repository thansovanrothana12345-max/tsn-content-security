import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from backend.app import app
from backend.database import get_db_connection
from backend.config import Config
from backend.worker import process_single_scan_job

client = TestClient(app)

@pytest.fixture(autouse=True)
def bypass_auth_setup():
    old_bypass = Config.DEVELOPMENT_BYPASS_AUTH
    Config.DEVELOPMENT_BYPASS_AUTH = True
    yield
    Config.DEVELOPMENT_BYPASS_AUTH = old_bypass

def test_health_ready_metrics():
    # Test Liveness /health
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json() == {"status": "healthy"}

    # Test Readiness /ready
    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    assert res_ready.json() == {"status": "ready"}

    # Test Observability /metrics
    res_metrics = client.get("/metrics")
    assert res_metrics.status_code == 200
    data = res_metrics.json()
    assert "status" in data
    assert "scan_jobs" in data
    assert "total_assets" in data
    assert "total_evidence" in data
    assert "storage_size_mb" in data

def test_pagination_and_sorting():
    # Test Assets listing pagination & sorting
    res_assets = client.get("/api/v1/assets?limit=5&offset=0&sort_by=filename&order=ASC")
    assert res_assets.status_code == 200
    assert isinstance(res_assets.json(), list)

    # Test Scans list pagination & sorting
    res_scans = client.get("/api/v1/scans/results?limit=2&sort_by=created_at&order=DESC")
    assert res_scans.status_code == 200
    assert isinstance(res_scans.json(), list)

@patch("backend.services.connectors.get_connector_for_url")
def test_scan_job_retry_success(mock_get_connector):
    # Mock connector failing once with network error, then succeeding on second attempt
    mock_conn = MagicMock()
    
    call_count = 0
    def mock_extract_metadata(url):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("Temporary connection timeout")
        return {
            "platform": "YouTube",
            "title": "Retry Success Video Title",
            "uploader": "Uploader Name",
            "upload_date": "2026-07-07",
            "thumbnail_url": None
        }
        
    mock_conn.extract_metadata.side_effect = mock_extract_metadata
    mock_conn.download_screenshot.return_value = None
    mock_conn.download_asset.return_value = None
    mock_get_connector.return_value = mock_conn
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO scan_jobs (url, platform, status) VALUES ('https://www.youtube.com/watch?v=retry', 'YouTube', 'Pending');")
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    job = {
        "id": job_id,
        "url": "https://www.youtube.com/watch?v=retry",
        "case_id": None,
        "created_by": 0,
        "platform": "YouTube"
    }
    
    with patch("time.sleep", return_value=None):  # Fast forward retry backoffs
        process_single_scan_job(job)
        
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, progress_percent, error_message FROM scan_jobs WHERE id = ?;", (job_id,))
    row = cursor.fetchone()
    conn.close()
    
    assert row["status"] == "Completed"
    assert call_count == 2
