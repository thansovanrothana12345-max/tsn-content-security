import httpx
import os
import sys
import pytest

BASE_URL = "http://127.0.0.1:8000"

def test_live_upload():
    # Skip if local development server is not running
    try:
        with httpx.Client() as client:
            client.get(BASE_URL, timeout=1.0)
    except Exception:
        pytest.skip("Local development server is not running at http://127.0.0.1:8000")

    print("Starting live integration test with httpx...")
    
    # 1. Login to get token
    login_url = f"{BASE_URL}/api/v1/auth/login"
    login_data = {"email": "admin", "password": "AdminPassword123"}
    
    with httpx.Client() as client:
        r = client.post(login_url, json=login_data)
        if r.status_code != 200:
            print(f"Login failed: {r.status_code} - {r.text}")
            sys.exit(1)
            
        token = r.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("Login successful!")
        
        # 2. Create a test case
        case_url = f"{BASE_URL}/api/v1/cases"
        case_data = {
            "title": "Live Upload Test Case",
            "client_name": "Test Client",
            "platform": "YouTube",
            "priority": "Medium",
            "description": "Integration test case"
        }
        r = client.post(case_url, json=case_data, headers=headers)
        if r.status_code != 201:
            print(f"Failed to create case: {r.status_code} - {r.text}")
            sys.exit(1)
            
        case_id = r.json()["id"]
        print(f"Created case ID: {case_id}")
        
        # 3. Upload the JPG file
        upload_url = f"{BASE_URL}/api/v1/evidence/upload/{case_id}"
        jpg_path = r"F:\TOOL\TSN Content Security\scratch\test_evidence.jpg"
        
        if not os.path.exists(jpg_path):
            print(f"Test JPG file not found at {jpg_path}")
            sys.exit(1)
            
        with open(jpg_path, "rb") as f:
            files = {"file": ("test_evidence.jpg", f, "image/jpeg")}
            r = client.post(upload_url, files=files, headers=headers)
            
        if r.status_code != 201:
            print(f"Upload failed: {r.status_code} - {r.text}")
            sys.exit(1)
            
        upload_result = r.json()
        print(f"Upload successful: {upload_result}")
        
        # 4. List evidence
        list_url = f"{BASE_URL}/api/v1/evidence/{case_id}"
        r = client.get(list_url, headers=headers)
        if r.status_code != 200:
            print(f"Failed to list evidence: {r.status_code} - {r.text}")
            sys.exit(1)
            
        evidence_list = r.json()
        print(f"Evidence list contents: {evidence_list}")
        
        # Assertions
        assert len(evidence_list) == 1, "Evidence list should contain exactly 1 item"
        assert evidence_list[0]["title"] == "test_evidence.jpg", "Title should match the uploaded filename"
        assert evidence_list[0]["file_type"] == "image/jpeg", "File type should be image/jpeg"
        
        # Try retrieving the file
        file_url = f"{BASE_URL}{evidence_list[0]['url']}"
        r = client.get(file_url, headers=headers)
        if r.status_code != 200:
            print(f"Failed to retrieve file content: {r.status_code} - {r.text}")
            sys.exit(1)
        print("Successfully retrieved file content from server!")
        
    print("\n--- ALL LIVE INTEGRATION TESTS PASSED SUCCESSFULLY! ---")

if __name__ == "__main__":
    test_live_upload()
