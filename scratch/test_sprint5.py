import sys
import os
import time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.app import app
from backend.database import init_db

client = TestClient(app, raise_server_exceptions=False)

def test_sprint5_features():
    print("--- Running Sprint 5 Enterprise Case Manager Integration Tests ---")
    init_db()
    
    # 1. Login Admin
    login_res = client.post("/api/v1/auth/login", json={"email": "admin", "password": "AdminPassword123"})
    assert login_res.status_code == 200
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Verify List of Users
    users_res = client.get("/api/v1/auth/users", headers=headers)
    assert users_res.status_code == 200
    users = users_res.json()
    assert len(users) > 0
    print("OK: Fetched system users list.")
    
    # 3. Create Case with Owner & Tags & Critical Priority
    case_payload = {
        "title": "Sprint 5 Critical Case",
        "client_name": "Acme Enterprise",
        "platform": "YouTube",
        "priority": "Critical",
        "description": "Enterprise workspace sprint test description.",
        "assigned_user_id": users[0]["id"],
        "tags": "sprint5,critical,video"
    }
    create_res = client.post("/api/v1/cases", json=case_payload, headers=headers)
    assert create_res.status_code == 201, f"Failed to create case: {create_res.text}"
    case = create_res.json()
    assert case["status"] == "Draft", f"Expected default status 'Draft', got '{case['status']}'"
    assert case["priority"] == "Critical"
    assert case["tags"] == "sprint5,critical,video"
    case_id = case["id"]
    print("OK: Created case with Owner, Tags, Critical Priority and Draft status.")
    
    # 4. Duplicate Case
    dup_res = client.post(f"/api/v1/cases/{case_id}/duplicate", headers=headers)
    assert dup_res.status_code == 201, f"Failed to duplicate case: {dup_res.text}"
    dup_case = dup_res.json()
    assert dup_case["title"] == f"Copy of Sprint 5 Critical Case"
    assert dup_case["status"] == "Draft"
    assert dup_case["priority"] == "Critical"
    assert dup_case["tags"] == "sprint5,critical,video"
    print("OK: Duplicated case successfully.")
    
    # 5. Archive Case
    arch_res = client.post(f"/api/v1/cases/{case_id}/archive", headers=headers)
    assert arch_res.status_code == 200, f"Failed to archive case: {arch_res.text}"
    # Verify status in database
    get_res = client.get("/api/v1/cases", headers=headers)
    cases_list = get_res.json()
    archived_case = next((c for c in cases_list if c["id"] == case_id), None)
    assert archived_case is not None
    assert archived_case["status"] == "Archived", f"Expected status 'Archived', got '{archived_case['status']}'"
    print("OK: Archived case successfully.")
    
    # 6. Pagination & Headers
    # Create multiple cases to verify pagination limit and X-Total-Count header
    for i in range(12):
        client.post("/api/v1/cases", json={
            "title": f"Pagination Case {i}",
            "client_name": "Pagination Client",
            "platform": "TikTok",
            "priority": "Low",
            "description": "Pagination test case."
        }, headers=headers)
        
    pag_res = client.get("/api/v1/cases?page=1&limit=10", headers=headers)
    assert pag_res.status_code == 200
    assert len(pag_res.json()) == 10
    total_count = pag_res.headers.get("X-Total-Count")
    assert total_count is not None
    assert int(total_count) >= 12
    print(f"OK: Server-side pagination and X-Total-Count header ({total_count}) verified successfully.")
    
    print("\nALL SPRINT 5 ENTERPRISE CASE MANAGER TESTS PASSED SUCCESSFULLY! OK.")

if __name__ == "__main__":
    try:
        test_sprint5_features()
        sys.exit(0)
    except AssertionError as e:
        print(f"\nTEST FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED EXCEPTION DURING TESTS: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
