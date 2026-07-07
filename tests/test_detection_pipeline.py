import pytest
from unittest.mock import MagicMock, patch
import os
import sqlite3
import json
from backend.database import get_db_connection
from backend.worker import process_single_scan_job
from backend.config import Config

@pytest.fixture(autouse=True)
def bypass_auth_setup():
    old_bypass = Config.DEVELOPMENT_BYPASS_AUTH
    Config.DEVELOPMENT_BYPASS_AUTH = True
    yield
    Config.DEVELOPMENT_BYPASS_AUTH = old_bypass

@patch("backend.services.connectors.get_connector_for_url")
def test_production_detection_pipeline_success(mock_get_connector):
    # Mock connector returning valid metadata and paths
    mock_conn = MagicMock()
    mock_conn.extract_metadata.return_value = {
        "platform": "YouTube",
        "title": "Production Test Video",
        "uploader": "Test Channel",
        "upload_date": "2026-07-07",
        "thumbnail_url": None
    }
    mock_conn.download_screenshot.return_value = "/tmp/dummy_screenshot.jpg"
    mock_conn.download_asset.return_value = None
    mock_get_connector.return_value = mock_conn

    # 1. Create original reference asset and case folder in DB
    conn = get_db_connection()
    cursor = conn.cursor()
    
    import uuid
    unique_ref_uuid = f"ref-{uuid.uuid4()}"
    unique_case_title = f"Test Case AI {uuid.uuid4()}"
    
    cursor.execute("INSERT INTO cases (title, description, status, priority) VALUES (?, 'Description', 'Active', 'Medium');", (unique_case_title,))
    case_id = cursor.lastrowid
    
    cursor.execute("""
        INSERT INTO originals (case_id, filename, file_uuid, storage_provider, filesize, duration)
        VALUES (?, 'original.mp4', ?, 'local', 1048576, 10.0);
    """, (case_id, unique_ref_uuid))
    orig_id = cursor.lastrowid
    
    cursor.execute("INSERT INTO scan_jobs (url, platform, status, created_by, case_id) VALUES ('https://www.youtube.com/watch?v=ai', 'YouTube', 'Pending', 1, ?);", (case_id,))
    job_id = cursor.lastrowid
    
    conn.commit()
    conn.close()

    # Stub fingerprinting and similarity checks to simulate high similarity
    with patch("backend.ai.services.orchestrator.AIServiceOrchestrator.ingest_fingerprint", return_value=1), \
         patch("backend.ai.services.orchestrator.AIServiceOrchestrator.check_similarity") as mock_sim, \
         patch("os.path.exists", return_value=True):
         
         mock_sim.return_value = {
             "overall_score": 0.88,
             "matches": {"perceptual_hash": 0.90, "embedding": 0.86},
             "decision": "Verified Copy"
         }
         
         job = {
             "id": job_id,
             "url": "https://www.youtube.com/watch?v=ai",
             "case_id": case_id,
             "created_by": 1,
             "platform": "YouTube"
         }
         process_single_scan_job(job)

    # 2. Assert evidence is updated with the correct score in DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, progress_percent, error_message FROM scan_jobs WHERE id = ?;", (job_id,))
    job_row = cursor.fetchone()
    
    cursor.execute("SELECT similarity_score, screenshot_path FROM evidence WHERE case_id = ?;", (case_id,))
    evidence_row = cursor.fetchone()
    conn.close()

    assert job_row["status"] == "Completed"
    assert evidence_row["similarity_score"] == 0.88

@patch("backend.services.connectors.get_connector_for_url")
def test_production_detection_pipeline_ai_failure(mock_get_connector):
    # Mock connector returning valid metadata and paths
    mock_conn = MagicMock()
    mock_conn.extract_metadata.return_value = {
        "platform": "YouTube",
        "title": "Failure Test Video",
        "uploader": "Test Channel",
        "upload_date": "2026-07-07",
        "thumbnail_url": None
    }
    mock_conn.download_screenshot.return_value = "/tmp/dummy_screenshot.jpg"
    mock_conn.download_asset.return_value = None
    mock_get_connector.return_value = mock_conn

    conn = get_db_connection()
    cursor = conn.cursor()
    import uuid
    unique_case_title = f"Test Case Failure {uuid.uuid4()}"
    cursor.execute("INSERT INTO cases (title, description, status, priority) VALUES (?, 'Description', 'Active', 'Medium');", (unique_case_title,))
    case_id = cursor.lastrowid
    cursor.execute("INSERT INTO scan_jobs (url, platform, status, created_by, case_id) VALUES ('https://www.youtube.com/watch?v=fail', 'YouTube', 'Pending', 1, ?);", (case_id,))
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()

    # Simulate AI models failure
    with patch("backend.ai.services.orchestrator.AIServiceOrchestrator.ingest_fingerprint", side_effect=RuntimeError("GPU out of memory")), \
         patch("os.path.exists", return_value=True):
         
         job = {
             "id": job_id,
             "url": "https://www.youtube.com/watch?v=fail",
             "case_id": case_id,
             "created_by": 1,
             "platform": "YouTube"
         }
         # The worker loop should NOT crash! It must fail the job in DB.
         process_single_scan_job(job)

    # Assert job is marked as Failed with correct error preserved
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT status, error_message FROM scan_jobs WHERE id = ?;", (job_id,))
    job_row = cursor.fetchone()
    conn.close()

    assert job_row["status"] == "Failed"
    assert "GPU out of memory" in job_row["error_message"]
