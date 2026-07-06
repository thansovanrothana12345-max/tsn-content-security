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

def setup_test_audit_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Clean old logs to make test assertions deterministic
    cursor.execute("DELETE FROM audit_logs")
    
    # Insert multiple audit logs
    cursor.execute("""
        INSERT INTO audit_logs (action, entity_type, details_json)
        VALUES ('TEST_ACTION_A', 'system', '{"info": "test log 1"}')
    """)
    cursor.execute("""
        INSERT INTO audit_logs (action, entity_type, details_json)
        VALUES ('TEST_ACTION_B', 'system', '{"info": "test log 2"}')
    """)
    cursor.execute("""
        INSERT INTO audit_logs (action, entity_type, details_json)
        VALUES ('TEST_ACTION_A', 'system', '{"info": "test log 3"}')
    """)
    
    conn.commit()
    conn.close()

def run_phase6_tests():
    print("--- Running Phase 6 Security Center Audit Tests ---")
    
    # Disable developer bypass
    old_bypass = Config.DEVELOPMENT_BYPASS_AUTH
    Config.DEVELOPMENT_BYPASS_AUTH = False
    
    setup_test_audit_logs()
    
    try:
        # 1. Login Admin to get token
        login_res = client.post("/api/v1/auth/login", json={"email": "admin", "password": "Admin123"})
        assert login_res.status_code == 200, "Admin login failed"
        admin_token = login_res.json()["token"]
        
        # 2. Login a Guest user
        guest_username = f"guest_{int(time.time())}"
        guest_email = f"{guest_username}@copyrightcenter.com"
        reg_res = client.post("/api/v1/auth/register", json={
            "username": guest_username,
            "email": guest_email,
            "password": "GuestPassword123",
            "role": "Guest"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert reg_res.status_code == 201, f"Guest registration failed"
        
        guest_login = client.post("/api/v1/auth/login", json={"email": guest_username, "password": "GuestPassword123"})
        assert guest_login.status_code == 200, "Guest login failed"
        guest_token = guest_login.json()["token"]
        
        # 3. Test: Guest access to audit logs is blocked with 403 Forbidden
        bad_res = client.get("/api/v1/auth/audit/logs", headers={"Authorization": f"Bearer {guest_token}"})
        assert bad_res.status_code == 403, f"Expected 403, got {bad_res.status_code}"
        print("OK: Non-Admin role blocked from audit logs.")
        
        # 4. Test: Admin can fetch all audit logs (should return 3 logs + registration audit entry if generated)
        logs_res = client.get("/api/v1/auth/audit/logs", headers={"Authorization": f"Bearer {admin_token}"})
        assert logs_res.status_code == 200
        logs = logs_res.json()
        assert len(logs) >= 3, f"Expected at least 3 logs, got {len(logs)}"
        
        # Check properties of logs
        log_keys = ["id", "user_id", "action", "entity_type", "entity_id", "details_json", "ip_address", "created_at"]
        for key in log_keys:
            assert key in logs[0], f"Key '{key}' missing in audit log entry"
            
        print("OK: Admin can retrieve audit logs with correct attributes.")
        
        # 5. Test: Action filter
        filtered_res = client.get("/api/v1/auth/audit/logs?action=TEST_ACTION_A", headers={"Authorization": f"Bearer {admin_token}"})
        assert filtered_res.status_code == 200
        filtered_logs = filtered_res.json()
        for l in filtered_logs:
            assert l["action"] == "TEST_ACTION_A", f"Expected action TEST_ACTION_A, got {l['action']}"
            
        print("OK: Audit logs action filtering works.")
        
        # 6. Test: Pagination (limit & offset)
        paged_res = client.get("/api/v1/auth/audit/logs?limit=2&offset=0", headers={"Authorization": f"Bearer {admin_token}"})
        assert paged_res.status_code == 200
        paged_logs = paged_res.json()
        assert len(paged_logs) == 2, f"Expected exactly 2 paged logs, got {len(paged_logs)}"
        
        print("OK: Audit logs pagination limit works.")
        
    finally:
        Config.DEVELOPMENT_BYPASS_AUTH = old_bypass

if __name__ == "__main__":
    try:
        run_phase6_tests()
        print("\nALL PHASE 6 TESTS PASSED SUCCESSFULLY! OK.")
        sys.exit(0)
    except AssertionError as e:
        print(f"\nTEST FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED EXCEPTION DURING TESTS: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
