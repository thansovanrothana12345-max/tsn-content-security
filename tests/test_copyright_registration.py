import pytest
from fastapi.testclient import TestClient
import os
import io
from backend.app import app
from backend.config import Config
from backend.routes.auth import get_current_user

@pytest.fixture(autouse=True)
def auth_bypass():
    old_val = Config.DEVELOPMENT_BYPASS_AUTH
    Config.DEVELOPMENT_BYPASS_AUTH = True
    yield
    Config.DEVELOPMENT_BYPASS_AUTH = old_val
    app.dependency_overrides.clear()

def test_upload_file_success():
    client = TestClient(app)
    
    file_content = b"This is a dummy test file content for copyright registry."
    file_name = "test_video.mp4"
    
    # Mock extract_file_metadata to return dummy stats
    from unittest.mock import patch
    with patch("backend.routes.copyright_registration.extract_file_metadata") as mock_extract:
        mock_extract.return_value = {
            "codec_properties": {
                "duration": 12.5,
                "width": 1920,
                "height": 1080,
                "codec": "h264",
                "fps": 30.0,
                "bitrate": 5000000,
                "channels": 2,
                "sample_rate": 48000
            }
        }
        
        response = client.post(
            "/api/v1/copyright/upload",
            files={"file": (file_name, io.BytesIO(file_content), "video/mp4")}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["filename"] == file_name
        assert data["category"] == "Video"
        assert "file_uuid" in data
        assert "sha256_hash" in data
        assert data["metadata"]["duration"] == 12.5
        assert data["metadata"]["resolution"] == "1920x1080"
        
        # Clean up temp file
        temp_file_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "storage", "temp", f"{data['file_uuid']}.mp4"
        )
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

def test_register_asset_and_crud():
    client = TestClient(app)
    
    # First, register an asset
    payload = {
        "asset_id": "TSNC-ASSET-MOCKTEST",
        "certificate_id": "TSNC-CERT-MOCKTEST",
        "registration_number": "REG-MOCKTEST",
        "asset_title": "Mock Testing Title",
        "description": "Integration testing asset description",
        "category": "Video",
        "owner_name": "John Doe Private Legal Name",
        "owner_email": "johndoe@test.com",
        "owner_phone": "+1234567890",
        "owner_address": "123 Private lane, NY",
        "organization": "Test Org",
        "country": "US",
        "creation_date": "2026-07-10",
        "copyright_type": "Registered",
        "license_type": "All Rights Reserved",
        "tags": "test, mock, video",
        "notes": "Internal developer notes",
        "file_uuid": "mock-uuid-1234",
        "filename": "mockfile.mp4",
        "file_size": 1024,
        "sha256_hash": "mock-sha256-hash-value-1234",
        "md5_hash": "mock-md5-hash-value-1234",
        "duration": 5.0,
        "resolution": "1280x720",
        "codec": "h264",
        "frame_rate": 24.0,
        "bitrate": 1000000,
        "audio_channels": 2,
        "thumbnail_path": "",
        "status": "Protected"
    }
    
    # 1. POST /register
    reg_response = client.post("/api/v1/copyright/register", json=payload)
    assert reg_response.status_code == 201
    reg_data = reg_response.json()
    assert reg_data["asset_id"] == "TSNC-ASSET-MOCKTEST"
    reg_id = reg_data["id"]
    
    try:
        # 2. GET /registrations (Admin view - should decrypt owner details)
        # Auth mock returns Admin role by default with Config.DEVELOPMENT_BYPASS_AUTH = True
        list_response = client.get("/api/v1/copyright/registrations?query=MOCKTEST")
        assert list_response.status_code == 200
        list_data = list_response.json()
        assert len(list_data) >= 1
        
        target_reg = [r for r in list_data if r["id"] == reg_id][0]
        assert target_reg["owner_name"] == "John Doe Private Legal Name"
        assert target_reg["owner_email"] == "johndoe@test.com"
        
        # 3. GET /registrations (Non-Admin view - should redact details)
        non_admin_user = {
            "id": 2,
            "username": "reviewer_user",
            "email": "reviewer@test.com",
            "role": "Reviewer"
        }
        app.dependency_overrides[get_current_user] = lambda: non_admin_user
        
        list_response_non_admin = client.get("/api/v1/copyright/registrations?query=MOCKTEST")
        assert list_response_non_admin.status_code == 200
        list_data_na = list_response_non_admin.json()
        target_reg_na = [r for r in list_data_na if r["id"] == reg_id][0]
        assert target_reg_na["owner_name"] == "[REDACTED]"
        assert target_reg_na["owner_email"] == "[REDACTED]"
        assert target_reg_na["owner_phone"] == "[REDACTED]"
        assert target_reg_na["owner_address"] == "[REDACTED]"

        # Clear override
        app.dependency_overrides.clear()

        # 4. PUT /registrations/{id} (Update details)
        payload["asset_title"] = "Updated Testing Title"
        update_response = client.put(f"/api/v1/copyright/registrations/{reg_id}", json=payload)
        assert update_response.status_code == 200
        
        # Verify update
        detail_response = client.get(f"/api/v1/copyright/registrations/{reg_id}")
        assert detail_response.status_code == 200
        assert detail_response.json()["asset_title"] == "Updated Testing Title"

        # 5. POST /registrations/{id}/archive (Archive registration)
        archive_response = client.post(f"/api/v1/copyright/registrations/{reg_id}/archive")
        assert archive_response.status_code == 200
        assert archive_response.json()["status"] == "success"
        
        detail_response = client.get(f"/api/v1/copyright/registrations/{reg_id}")
        assert detail_response.json()["status"] == "Archived"
        
    finally:
        # 6. DELETE /registrations/{id} (Cleanup registration)
        delete_response = client.delete(f"/api/v1/copyright/registrations/{reg_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["status"] == "success"
