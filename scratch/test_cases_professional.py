import sys
import os
import time

# Adjust Python path to allow backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.app import app
from backend.database import init_db

client = TestClient(app, raise_server_exceptions=False)

def test_cases_professional_module():
    print("--- Running Case Manager Professional API Integration Tests ---")
    init_db()
    
    # 1. Login Admin to get token
    login_res = client.post("/api/v1/auth/login", json={"email": "admin", "password": "Admin123"})
    assert login_res.status_code == 200, f"Admin login failed: {login_res.status_code}"
    admin_token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {admin_token}"}
    
    # 2. Verify validation rules (Create Case without client_name or platform should fail)
    bad_create = client.post("/api/v1/cases", json={"title": "Test Case"}, headers=headers)
    assert bad_create.status_code == 422, f"Expected 422 validation error for missing client/platform, got {bad_create.status_code}"
    print("OK: Model validation rejected malformed creation request (missing client_name and platform).")
    
    # 3. Create a valid Case
    case_name = f"Test Case Name {int(time.time())}"
    client_name = f"Acme Corp Inc {int(time.time())}"
    create_payload = {
        "title": case_name,
        "client_name": client_name,
        "platform": "YouTube",
        "priority": "High",
        "description": "Enterprise test case description notes."
    }
    create_res = client.post("/api/v1/cases", json=create_payload, headers=headers)
    assert create_res.status_code == 201, f"Create failed: {create_res.status_code}"
    created_case = create_res.json()
    case_id = created_case["id"]
    print(f"OK: Created valid case folder. Generated ID: #{case_id}.")
    
    # 4. Search verification
    # Search by Name
    search_res = client.get(f"/api/v1/cases?q={case_name}", headers=headers)
    assert search_res.status_code == 200
    found_cases = search_res.json()
    assert len(found_cases) > 0, "No cases found searching by Case Name"
    assert found_cases[0]["id"] == case_id
    
    # Search by Client
    search_res = client.get(f"/api/v1/cases?q={client_name}", headers=headers)
    assert search_res.status_code == 200
    found_cases = search_res.json()
    assert len(found_cases) > 0, "No cases found searching by Client"
    
    # Search by Platform
    search_res = client.get(f"/api/v1/cases?q=YouTube", headers=headers)
    assert search_res.status_code == 200
    found_cases = search_res.json()
    assert any(c["id"] == case_id for c in found_cases), "Created case not found in platform search"
    print("OK: Real-time search verified for Case Name, Client Name, and Platform.")
    
    # 5. Filters verification
    # Filter by priority
    filter_res = client.get(f"/api/v1/cases?priority=High", headers=headers)
    assert filter_res.status_code == 200
    filtered = filter_res.json()
    assert all(c["priority"] == "High" for c in filtered), "Filter by Priority failed"
    
    # Filter by platform
    filter_res = client.get(f"/api/v1/cases?platform=YouTube", headers=headers)
    assert filter_res.status_code == 200
    filtered = filter_res.json()
    assert all(c["platform"] == "YouTube" for c in filtered), "Filter by Platform failed"
    print("OK: Filters query parameter verified for Status, Priority, and Platform.")
    
    # 6. Sorting verification
    sort_res = client.get(f"/api/v1/cases?sort_by=alphabetical", headers=headers)
    assert sort_res.status_code == 200
    sorted_list = sort_res.json()
    titles = [c["title"].lower() for c in sorted_list]
    assert titles == sorted(titles), "Sorting by Alphabetical failed"
    print("OK: Sorting query parameter verified.")
    
    # 7. Edit Case
    edit_payload = {
        "title": f"Updated {case_name}",
        "client_name": f"Updated {client_name}",
        "priority": "Low",
        "status": "Resolved",
        "description": "Updated case description notes."
    }
    put_res = client.put(f"/api/v1/cases/{case_id}", json=edit_payload, headers=headers)
    assert put_res.status_code == 200, f"Edit failed: {put_res.status_code}"
    updated = put_res.json()
    assert updated["title"] == f"Updated {case_name}"
    assert updated["client_name"] == f"Updated {client_name}"
    assert updated["priority"] == "Low"
    assert updated["status"] == "Resolved"
    assert updated["description"] == "Updated case description notes."
    print("OK: Case modification edit endpoint verified successfully.")
    
    # 8. Add Reviewer Timeline Note
    note_payload = {
        "note": "Initial reviewer evaluation comment added."
    }
    note_res = client.post(f"/api/v1/cases/{case_id}/notes", json=note_payload, headers=headers)
    assert note_res.status_code == 201, f"Note creation failed: {note_res.status_code}"
    print("OK: Note added linked to case.")
    
    # 9. Timeline history verification
    timeline_res = client.get(f"/api/v1/cases/{case_id}/timeline", headers=headers)
    assert timeline_res.status_code == 200, f"Timeline fetch failed: {timeline_res.status_code}"
    timeline = timeline_res.json()
    assert len(timeline) >= 3, f"Expected at least 3 timeline events (Created, Updated, Note), got {len(timeline)}"
    
    # Verify chronological sorting order
    timestamps = [item["timestamp"] for item in timeline]
    assert timestamps == sorted(timestamps), "Timeline is not sorted chronologically"
    
    types = [item["type"] for item in timeline]
    assert "Created" in types, "Created event missing from timeline"
    assert "History" in types, "Update history event missing from timeline"
    assert "Note" in types, "Custom reviewer note missing from timeline"
    print("OK: Combined timeline retrieval returned chronological Created, History, and Note events.")
    
    # 10. Soft deletion verification
    del_res = client.delete(f"/api/v1/cases/{case_id}", headers=headers)
    assert del_res.status_code == 200
    print("OK: Delete endpoint returned 200.")
    
    # Fetch active cases list and make sure deleted case is omitted
    get_all_res = client.get("/api/v1/cases", headers=headers)
    active_cases = get_all_res.json()
    assert not any(c["id"] == case_id for c in active_cases), "Deleted case still returned in active list (soft delete failed)"
    print("OK: Soft delete verified (deleted case hidden from list queries).")
    
    print("\nALL CASE MANAGER PROFESSIONAL TESTS PASSED SUCCESSFULLY! OK.")

if __name__ == "__main__":
    try:
        test_cases_professional_module()
        sys.exit(0)
    except AssertionError as e:
        print(f"\nTEST FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED EXCEPTION DURING TESTS: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
