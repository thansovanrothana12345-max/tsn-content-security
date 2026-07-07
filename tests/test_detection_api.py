import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import os
import tempfile
from backend.app import app
from backend.config import Config

@pytest.fixture(autouse=True)
def auth_bypass():
    old_val = Config.DEVELOPMENT_BYPASS_AUTH
    Config.DEVELOPMENT_BYPASS_AUTH = True
    yield
    Config.DEVELOPMENT_BYPASS_AUTH = old_val

def test_api_detection_check_success():
    client = TestClient(app)
    
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        # Mock detection service calculations
        with patch("backend.routes.detection.DetectionService.run_detection_check") as mock_run:
            mock_run.return_value = {
                "evidence_id": 12,
                "case_id": 34,
                "overall_similarity": 0.85,
                "confidence_score": 0.80,
                "confidence_level": "High",
                "explanation": "Visual match copy discovered.",
                "modality_scores": {
                    "visual": 0.88,
                    "acoustic": 0.0,
                    "ocr": 0.0,
                    "logo": 0.0,
                    "metadata": 0.0
                },
                "agreements": []
            }
            
            payload = {
                "case_id": 34,
                "evidence_id": 12,
                "asset_file": tmp_path
            }
            
            response = client.post("/api/v1/detection/check", json=payload)
            assert response.status_code == 200
            data = response.json()
            assert data["evidence_id"] == 12
            assert data["case_id"] == 34
            assert data["overall_similarity"] == 0.85
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

def test_api_detection_check_not_found():
    client = TestClient(app)
    
    payload = {
        "case_id": 34,
        "evidence_id": 12,
        "asset_file": "nonexistent_file_path.mp4"
    }
    
    response = client.post("/api/v1/detection/check", json=payload)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

@patch("backend.routes.detection.get_db_connection")
def test_api_detection_status_route(mock_db):
    client = TestClient(app)
    
    # Stub database row
    mock_conn = MagicMock()
    mock_cursor = mock_conn.cursor.return_value
    mock_cursor.fetchone.return_value = ("Completed", 100.0, None)
    mock_db.return_value = mock_conn
    
    response = client.get("/api/v1/detection/status/101")
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == 101
    assert data["status"] == "Completed"
    assert data["progress_percent"] == 100.0
