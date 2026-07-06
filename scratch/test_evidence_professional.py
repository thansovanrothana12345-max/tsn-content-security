import sys
import os
import time

# Adjust Python path to allow backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.app import app
from backend.database import init_db

client = TestClient(app, raise_server_exceptions=False)

def test_evidence_professional_module():
    print("--- Running Evidence Management Professional Integration Tests ---")
    init_db()
    
    # 1. Login Admin to get token
    login_res = client.post("/api/v1/auth/login", json={"email": "admin", "password": "AdminPassword123"})
    assert login_res.status_code == 200, f"Admin login failed: {login_res.status_code}"
    admin_token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 2. Create a case to link evidence to
    case_name = f"Evidence Test Case {int(time.time())}"
    case_res = client.post("/api/v1/cases", json={
        "title": case_name,
        "client_name": "Acme Corp",
        "platform": "YouTube",
        "priority": "Medium",
        "description": "Case folder for evidence upload tests."
    }, headers=headers)
    assert case_res.status_code == 201
    case_id = case_res.json()["id"]
    print(f"OK: Created target Case ID #{case_id} for linkage.")
    
    # 3. Simulate image upload
    image_content = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01..."
    upload_res = client.post(
        f"/api/v1/evidence/upload/{case_id}",
        files={"file": ("screenshot.png", image_content, "image/png")},
        headers=headers
    )
    assert upload_res.status_code == 201, f"Image upload failed: {upload_res.status_code}"
    img_data = upload_res.json()
    assert img_data["filename"] == "screenshot.png"
    assert img_data["file_type"] == "image/png"
    assert img_data["file_size"] > 0
    img_evidence_id = img_data["id"]
    img_url = img_data["url"]
    print(f"OK: Uploaded valid image file (Evidence ID #{img_evidence_id}, URL: {img_url}).")
    
    # 4. Simulate PDF document upload
    pdf_content = b"%PDF-1.4 ... test pdf content"
    upload_res2 = client.post(
        f"/api/v1/evidence/upload/{case_id}",
        files={"file": ("brief.pdf", pdf_content, "application/pdf")},
        headers=headers
    )
    assert upload_res2.status_code == 201
    doc_data = upload_res2.json()
    assert doc_data["filename"] == "brief.pdf"
    assert doc_data["file_type"] == "application/pdf"
    doc_evidence_id = doc_data["id"]
    print(f"OK: Uploaded valid document file (Evidence ID #{doc_evidence_id}).")
    
    # 5. Safety validation check (Reject unsafe executable files)
    exe_content = b"MZ\x90\x00\x03\x00\x00\x00... malware simulation"
    bad_upload = client.post(
        f"/api/v1/evidence/upload/{case_id}",
        files={"file": ("payload.exe", exe_content, "application/octet-stream")},
        headers=headers
    )
    assert bad_upload.status_code == 400, f"Expected rejection of .exe, got {bad_upload.status_code}"
    print("OK: Securely rejected unsafe file extension (.exe).")
    
    # 6. Safety validation check (Reject script files)
    bat_content = b"@echo off\necho maldoc"
    bad_upload2 = client.post(
        f"/api/v1/evidence/upload/{case_id}",
        files={"file": ("exploit.bat", bat_content, "application/x-bat")},
        headers=headers
    )
    assert bad_upload2.status_code == 400
    print("OK: Securely rejected script executable extension (.bat).")
    
    # 7. Check Search & Filters on list_evidence endpoint
    # Query all evidence
    list_all = client.get(f"/api/v1/evidence/{case_id}", headers=headers)
    assert list_all.status_code == 200
    items = list_all.json()
    assert len(items) == 2, f"Expected 2 evidence items, got {len(items)}"
    
    # Search by Title
    list_search = client.get(f"/api/v1/evidence/{case_id}?q=brief", headers=headers)
    assert len(list_search.json()) == 1
    assert list_search.json()[0]["id"] == doc_evidence_id
    
    # Filter by Type (Image)
    list_images = client.get(f"/api/v1/evidence/{case_id}?file_type=image", headers=headers)
    assert len(list_images.json()) == 1
    assert list_images.json()[0]["id"] == img_evidence_id
    
    # Filter by Type (Document)
    list_docs = client.get(f"/api/v1/evidence/{case_id}?file_type=document", headers=headers)
    assert len(list_docs.json()) == 1
    assert list_docs.json()[0]["id"] == doc_evidence_id
    print("OK: Evidence filtering and query searching returned precise filtered datasets.")
    
    # 8. Retrieve/Download file content securely
    file_retrieve = client.get(img_url, headers=headers)
    assert file_retrieve.status_code == 200, f"Failed to retrieve file content: {file_retrieve.status_code}"
    assert file_retrieve.content == image_content, "Downloaded content does not match uploaded data"
    print("OK: Download endpoint retrieved content correctly and verified checksum matches.")
    
    # 9. Path traversal attempt check
    bad_retrieve = client.get("/api/v1/evidence/file/../../main.py", headers=headers)
    assert bad_retrieve.status_code in [400, 404], f"Expected 400/404 path traversal blocking, got {bad_retrieve.status_code}"
    print("OK: Path traversal attack blocked successfully.")
    
    # 10. File purge on deletion
    # Get the unique storage file path
    filename = os.path.basename(img_url)
    PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    physical_path = os.path.join(PROJECT_ROOT, "storage", "evidence", filename)
    assert os.path.exists(physical_path), "Physical file missing on storage directory"
    
    # Perform DELETE API call
    del_res = client.delete(f"/api/v1/evidence/{img_evidence_id}", headers=headers)
    assert del_res.status_code == 200
    
    # Ensure physical file is deleted
    assert not os.path.exists(physical_path), "Physical file was not cleaned from disk storage after deletion"
    print("OK: Delete endpoint successfully removed database records and purged storage file from disk.")
    
    print("\nALL EVIDENCE MANAGEMENT PROFESSIONAL TESTS PASSED SUCCESSFULLY! OK.")

if __name__ == "__main__":
    try:
        test_evidence_professional_module()
        sys.exit(0)
    except AssertionError as e:
        print(f"\nTEST FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED EXCEPTION DURING TESTS: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
