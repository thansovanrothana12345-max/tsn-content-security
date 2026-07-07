import os
import json
import time
import pytest
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

def test_asset_library_flow():
    # Ingest a brand logo asset using random bytes to prevent sha256 duplicates
    import random
    file_bytes = f"fake_png_data_{random.randint(0, 10000000)}".encode()
    logo_file = ("logo.png", file_bytes, "image/png")
    res = client.post(
        "/api/v1/assets",
        data={"asset_type": "Logo"},
        files={"file": logo_file}
    )
    assert res.status_code == 201
    asset = res.json()
    assert asset["asset_type"] == "Logo"
    assert asset["filename"] == "logo.png"
    assert "sha256_hash" in asset
    
    # Retrieve asset details
    asset_id = asset["id"]
    get_res = client.get(f"/api/v1/assets/{asset_id}")
    assert get_res.status_code == 200
    assert get_res.json()["filename"] == "logo.png"
    
    # List assets
    list_res = client.get("/api/v1/assets")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

def test_scan_center_async_pipeline():
    # Start Scan - valid YouTube URL
    scan_res = client.post(
        "/api/v1/scans",
        json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}
    )
    assert scan_res.status_code == 202
    job = scan_res.json()
    assert job["status"] == "Pending"
    assert job["platform"] == "YouTube"
    job_id = job["job_id"]
    
    # Get scan status
    status_res = client.get(f"/api/v1/scans/{job_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "Pending"
    
    # Start Scan - invalid URL rejection (empty netloc)
    bad_res = client.post(
        "/api/v1/scans",
        json={"url": "https://"}
    )
    assert bad_res.status_code == 400
    assert "error" in bad_res.json()["detail"]

def test_evidence_viewer_and_chain():
    # Seed a fake scan result in DB
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scan_jobs (url, platform, status)
        VALUES ('https://www.instagram.com/reel/Co123/', 'Instagram', 'Completed');
    """)
    job_id = cursor.lastrowid
    cursor.execute("""
        INSERT INTO scan_results (job_id, url, platform, title, uploader, upload_date, screenshot_path)
        VALUES (?, 'https://www.instagram.com/reel/Co123/', 'Instagram', 'Test Reel', 'uploader_name', '2026-07-07', '/storage/evidence/screenshot.jpg');
    """, (job_id,))
    result_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # Promote scan result to immutable evidence
    promo_res = client.post(
        "/api/v1/evidence/create",
        json={"scan_result_id": result_id}
    )
    assert promo_res.status_code == 201
    evidence = promo_res.json()
    assert evidence["platform"] == "Instagram"
    assert evidence["title"] == "Test Reel"
    evidence_id = evidence["id"]
    
    # Attach evidence to case
    # Let's seed a case
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO cases (title, status, priority) VALUES ('Test Brand Protection Case', 'Draft', 'High');")
    case_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    attach_res = client.post(
        "/api/v1/evidence/attach",
        json={"evidence_id": evidence_id, "case_id": case_id}
    )
    assert attach_res.status_code == 201
    
    # View evidence detailed page with Chain of Custody / Audit logs
    view_res = client.get(f"/api/v1/evidence/view/{evidence_id}")
    assert view_res.status_code == 200
    details = view_res.json()
    assert details["platform"] == "Instagram"
    assert details["url"] == "https://www.instagram.com/reel/Co123/"
    assert len(details["attached_cases"]) >= 1
    assert len(details["audit_history"]) >= 1

def test_worker_scan_job_processing():
    # 1. Queue a job in scan_jobs
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scan_jobs (url, platform, status, progress_percent, created_by)
        VALUES ('https://www.youtube.com/watch?v=dQw4w9WgXcQ', 'YouTube', 'Pending', 0.0, 0);
    """)
    job_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    # 2. Invoke worker processing directly
    job = {
        "id": job_id,
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "case_id": None,
        "created_by": 0
    }
    process_single_scan_job(job)
    
    # 3. Verify database updates
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Verify scan_jobs status
    cursor.execute("SELECT status, progress_percent, error_message FROM scan_jobs WHERE id = ?;", (job_id,))
    job_row = cursor.fetchone()
    assert job_row["status"] == "Completed"
    assert job_row["progress_percent"] == 100.0
    
    # Verify scan_results entry exists
    cursor.execute("SELECT * FROM scan_results WHERE job_id = ?;", (job_id,))
    res_row = cursor.fetchone()
    assert res_row is not None
    assert res_row["platform"] == "YouTube"
    
    # Verify Evidence was created
    cursor.execute("SELECT * FROM evidence WHERE url = ? ORDER BY id DESC LIMIT 1;", ('https://www.youtube.com/watch?v=dQw4w9WgXcQ',))
    ev_row = cursor.fetchone()
    assert ev_row is not None
    
    # Verify auto-created Case exists
    cursor.execute("SELECT * FROM cases WHERE id = ?;", (ev_row["case_id"],))
    case_row = cursor.fetchone()
    assert case_row is not None
    assert case_row["title"].startswith("YouTube")
    
    # Verify case_evidence link exists
    cursor.execute("SELECT * FROM case_evidence WHERE case_id = ? AND evidence_id = ?;", (case_row["id"], ev_row["id"]))
    link_row = cursor.fetchone()
    assert link_row is not None
    
    conn.close()

