import sys
import os
import time

# Adjust Python path to allow backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.app import app
from backend.config import Config
from backend.database import get_db_connection

client = TestClient(app)

def setup_test_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Insert a test case
    cursor.execute("INSERT INTO cases (title, description, status) VALUES ('Analytics Test Case', 'Dashboard verification case', 'Active')")
    case_id = cursor.lastrowid
    
    # 2. Insert test evidence entries
    cursor.execute("""
        INSERT INTO evidence (case_id, platform, url, title, uploader, upload_date, similarity_score, status)
        VALUES (?, 'YouTube', 'https://www.youtube.com/watch?v=y1', 'Copy 1', 'john', '2026-07-04', 0.85, 'Verified')
    """, (case_id,))
    cursor.execute("""
        INSERT INTO evidence (case_id, platform, url, title, uploader, upload_date, similarity_score, status)
        VALUES (?, 'TikTok', 'https://www.tiktok.com/@t1', 'Copy 2', 'mary', '2026-07-04', 0.50, 'Detected')
    """, (case_id,))
    cursor.execute("""
        INSERT INTO evidence (case_id, platform, url, title, uploader, upload_date, similarity_score, status)
        VALUES (?, 'Facebook', 'https://www.facebook.com/f1', 'Copy 3', 'bob', '2026-07-04', 0.20, 'Detected')
    """, (case_id,))
    
    conn.commit()
    conn.close()
    return case_id

def cleanup_test_data(case_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cases WHERE id = ?", (case_id,))
    conn.commit()
    conn.close()

def run_phase5_tests():
    print("--- Running Phase 5 Analytics Dashboard Tests ---")
    
    # Disable developer bypass
    old_bypass = Config.DEVELOPMENT_BYPASS_AUTH
    Config.DEVELOPMENT_BYPASS_AUTH = False
    
    case_id = setup_test_data()
    
    try:
        # 1. Login Admin to get token
        login_res = client.post("/api/v1/auth/login", json={"email": "admin", "password": "AdminPassword123"})
        assert login_res.status_code == 200, "Admin login failed"
        admin_token = login_res.json()["token"]
        
        # 2. Get cases list and check that our test case exists
        cases_res = client.get("/api/v1/cases", headers={"Authorization": f"Bearer {admin_token}"})
        assert cases_res.status_code == 200
        cases_list = cases_res.json()
        assert len(cases_list) > 0
        target_case = next((c for c in cases_list if c["id"] == case_id), None)
        assert target_case is not None, "Created test case not returned in /api/v1/cases"
        
        # 3. Get evidence list for our test case
        evidence_res = client.get(f"/api/v1/evidence/{case_id}", headers={"Authorization": f"Bearer {admin_token}"})
        assert evidence_res.status_code == 200, f"Failed to get evidence: {evidence_res.text}"
        evidence_list = evidence_res.json()
        
        # Verify counts and properties
        assert len(evidence_list) == 3, f"Expected 3 evidence items, got {len(evidence_list)}"
        
        platforms = [ev["platform"] for ev in evidence_list]
        assert "YouTube" in platforms
        assert "TikTok" in platforms
        assert "Facebook" in platforms
        
        scores = [ev["similarity_score"] for ev in evidence_list]
        assert 0.85 in scores
        assert 0.50 in scores
        assert 0.20 in scores
        
        print("OK: Analytics data matches database records correctly.")
        
    finally:
        Config.DEVELOPMENT_BYPASS_AUTH = old_bypass
        cleanup_test_data(case_id)

if __name__ == "__main__":
    try:
        run_phase5_tests()
        print("\nALL PHASE 5 TESTS PASSED SUCCESSFULLY! OK.")
        sys.exit(0)
    except AssertionError as e:
        print(f"\nTEST FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED EXCEPTION DURING TESTS: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
