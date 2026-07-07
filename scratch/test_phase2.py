import sys
import os
import time

# Adjust Python path to allow backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.app import app
from backend.routes.auth import encode_jwt, decode_jwt
from backend.database import hash_password, get_db_connection
from backend.config import Config

client = TestClient(app)

def run_phase2_tests():
    print("--- Running Phase 2 Auth/RBAC Tests ---")
    
    # Enable auth validation and disable developer bypass
    old_bypass = Config.DEVELOPMENT_BYPASS_AUTH
    Config.DEVELOPMENT_BYPASS_AUTH = False
    
    try:
        # 1. Verify that protected endpoints block access when unauthenticated (no token)
        endpoints = [
            ("/api/v1/cases", "GET"),
            ("/api/v1/cases", "POST"),
            ("/api/v1/originals/9999", "GET"),
            ("/api/v1/evidence/9999", "GET"),
            ("/api/v1/evidence/scan", "POST"),
            ("/api/v1/reports/9999", "GET"),
            ("/api/v1/reports/generate", "POST"),
            ("/api/v1/auth/audit/logs", "GET")
        ]
        
        for url, method in endpoints:
            if method == "GET":
                res = client.get(url)
            elif method == "POST":
                res = client.post(url, json={})
            assert res.status_code == 401, f"Unauthenticated request to {method} {url} allowed with status {res.status_code}"
            assert res.json()["detail"]["error"] == "UNAUTHORIZED", f"Unexpected details response: {res.text}"
            
        print("OK: All protected endpoints correctly block unauthenticated access.")
        
        # 2. Login admin to get valid token
        login_res = client.post("/api/v1/auth/login", json={
            "email": "admin",
            "password": "AdminPassword123"
        })
        assert login_res.status_code == 200, "Admin login failed"
        admin_token = login_res.json()["token"]
        
        # 3. Create a Guest user using Admin token
        guest_username = f"guest_user_{int(time.time())}"
        guest_email = f"guest_{int(time.time())}@copyrightcenter.com"
        guest_password = "GuestPassword123"
        
        reg_res = client.post("/api/v1/auth/register", json={
            "username": guest_username,
            "email": guest_email,
            "password": guest_password,
            "role": "Guest"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert reg_res.status_code == 201, f"User registration failed: {reg_res.text}"
        print(f"OK: Admin successfully registered new Guest user '{guest_username}'.")
        
        # 4. Login as the newly created Guest user
        guest_login_res = client.post("/api/v1/auth/login", json={
            "email": guest_username,
            "password": guest_password
        })
        assert guest_login_res.status_code == 200, "Guest login failed"
        guest_token = guest_login_res.json()["token"]
        
        # 5. Access roles/me with Guest token and verify role is Guest
        me_res = client.get("/api/v1/auth/roles/me", headers={"Authorization": f"Bearer {guest_token}"})
        assert me_res.status_code == 200, "roles/me failed for Guest"
        assert me_res.json()["role"] == "Guest", "Role was not Guest"
        print("OK: /roles/me returns correct role mapping.")
        
        # 6. Verify that Guest user can call public registration endpoint (201 Created)
        bad_reg_res = client.post("/api/v1/auth/register", json={
            "username": f"hacker_{int(time.time())}",
            "email": f"hacker_{int(time.time())}@copyrightcenter.com",
            "password": "HackPassword123",
            "role": "Admin"
        }, headers={"Authorization": f"Bearer {guest_token}"})
        assert bad_reg_res.status_code == 201, f"Guest was not allowed to call register: {bad_reg_res.status_code}"
        print("OK: Public user registration allowed for Guest user role.")
        
        # 7. Verify that Guest user is BLOCKED from system audit logs endpoint (403 Forbidden)
        bad_audit_res = client.get("/api/v1/auth/audit/logs", headers={"Authorization": f"Bearer {guest_token}"})
        assert bad_audit_res.status_code == 403, f"Guest was allowed to call audit/logs: {bad_audit_res.status_code}"
        assert bad_audit_res.json()["detail"]["error"] == "FORBIDDEN", f"Incorrect error code: {bad_audit_res.text}"
        print("OK: System audit logs require Admin role and block Guests with 403 Forbidden.")
        
    finally:
        Config.DEVELOPMENT_BYPASS_AUTH = old_bypass

if __name__ == "__main__":
    try:
        run_phase2_tests()
        print("\nALL PHASE 2 TESTS PASSED SUCCESSFULLY! OK.")
        sys.exit(0)
    except AssertionError as e:
        print(f"\nTEST FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED EXCEPTION DURING TESTS: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
