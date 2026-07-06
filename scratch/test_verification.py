import sys
import os
import time

# Adjust Python path to allow backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app, raise_server_exceptions=False)

def test_verification_module():
    print("--- Running Verification Center API Integration Tests ---")
    
    # 1. Login Admin to get token
    login_res = client.post("/api/v1/auth/login", json={"email": "admin", "password": "AdminPassword123"})
    assert login_res.status_code == 200, "Admin login failed"
    admin_token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 2. Get verification list
    get_res = client.get("/api/v1/verification", headers=headers)
    assert get_res.status_code == 200, f"Failed to list verifications: {get_res.status_code}"
    records = get_res.json()
    print(f"OK: Listed verifications (found {len(records)} records).")
    
    # Ensure some verification record exists (if none exists, create a case first)
    if len(records) == 0:
        # Create case first
        case_res = client.post("/api/v1/cases", json={"title": "Verification Test Case"}, headers=headers)
        assert case_res.status_code == 201
        case_id = case_res.json()["id"]
        
        # Trigger reload/re-fetch to auto-create record
        get_res = client.get("/api/v1/verification", headers=headers)
        assert get_res.status_code == 200
        records = get_res.json()
        
    assert len(records) > 0, "No verification records found after case auto-sync."
    target_rec = records[0]
    rec_id = target_rec["id"]
    print(f"OK: Target verification record ID is #{rec_id}.")
    
    # 3. Update Verification Record details (Reviewer notes, status, metadata validations)
    update_payload = {
        "status": "Verified",
        "metadata_validation": "Verified",
        "hash_verification": "Verified",
        "reviewer_notes": "All checks validated and confirmed correct."
    }
    put_res = client.put(f"/api/v1/verification/{rec_id}", json=update_payload, headers=headers)
    assert put_res.status_code == 200, f"Update failed: {put_res.status_code}"
    print("OK: Verification record update endpoint returned 200.")
    
    # 4. Fetch list again to verify changes are committed
    verify_get_res = client.get("/api/v1/verification", headers=headers)
    records_updated = verify_get_res.json()
    updated_rec = next((r for r in records_updated if r["id"] == rec_id), None)
    
    assert updated_rec is not None, "Record not found in list after update."
    assert updated_rec["status"] == "Verified", f"Expected 'Verified' status, got {updated_rec['status']}"
    assert updated_rec["metadata_validation"] == "Verified"
    assert updated_rec["hash_verification"] == "Verified"
    assert len(updated_rec["notes"]) > 0, "No notes found on notes list."
    assert updated_rec["notes"][0]["note"] == "All checks validated and confirmed correct."
    print("OK: Updates, metadata validation, hash checks, and notes verified on API response.")
    
    # 5. Access check: Guest cannot modify verification records
    guest_username = f"guest_reviewer_{int(time.time())}"
    guest_login = client.post("/api/v1/auth/register", json={
        "username": guest_username,
        "email": f"guest_rev_{int(time.time())}@example.com",
        "password": "GuestPassword123",
        "role": "Guest"
    }, headers=headers)
    assert guest_login.status_code == 201
    
    guest_login_res = client.post("/api/v1/auth/login", json={
        "email": guest_username,
        "password": "GuestPassword123"
    })
    assert guest_login_res.status_code == 200
    guest_token = guest_login_res.json()["token"]
    guest_headers = {"Authorization": f"Bearer {guest_token}"}
    
    forbidden_put = client.put(f"/api/v1/verification/{rec_id}", json={"status": "Rejected"}, headers=guest_headers)
    assert forbidden_put.status_code == 403, f"Expected 403 forbidden for Guest user update, got {forbidden_put.status_code}"
    print("OK: Role access permissions verified (Guest role modifications rejected).")
    
    print("\nALL VERIFICATION CENTER INTEGRATION TESTS PASSED SUCCESSFULLY! OK.")

if __name__ == "__main__":
    try:
        test_verification_module()
        sys.exit(0)
    except AssertionError as e:
        print(f"\nTEST FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED EXCEPTION DURING TESTS: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
