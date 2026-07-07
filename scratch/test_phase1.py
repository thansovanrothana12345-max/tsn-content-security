import sys
import os
import time
import json
from datetime import datetime, timedelta

# Adjust Python path to allow backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.app import app
from backend.routes.auth import encode_jwt, decode_jwt, base64url_encode, base64url_decode
from backend.database import hash_password, get_db_connection
from backend.config import Config

client = TestClient(app)

def run_unit_tests():
    print("--- Running JWT Unit Tests ---")
    secret = "test-secret-key-12345"
    
    # 1. Base64url checks
    original_bytes = b"Hello, World! @#$%^&*()"
    encoded = base64url_encode(original_bytes)
    decoded = base64url_decode(encoded)
    assert decoded == original_bytes, "Base64URL roundtrip failed"
    print("OK: Base64URL encoding/decoding works.")
    
    # 2. JWT Encoding and Decoding
    payload = {"sub": 42, "role": "Admin", "exp": int(time.time()) + 10}
    token = encode_jwt(payload, secret)
    
    decoded_payload = decode_jwt(token, secret)
    assert decoded_payload["sub"] == 42, "JWT sub claim mismatch"
    assert decoded_payload["role"] == "Admin", "JWT role claim mismatch"
    print("OK: JWT encoding/decoding with valid signature works.")
    
    # 3. Signature tampering detection
    parts = token.split('.')
    tampered_sig = parts[2][:-5] + "AAAAA"
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"
    
    try:
        decode_jwt(tampered_token, secret)
        assert False, "JWT decoder accepted tampered signature"
    except ValueError as e:
        assert "Signature verification failed" in str(e), f"Unexpected signature error: {e}"
    print("OK: JWT signature tampering successfully blocked.")
    
    # 4. Token expiration
    expired_payload = {"sub": 42, "role": "Admin", "exp": int(time.time()) - 10}
    expired_token = encode_jwt(expired_payload, secret)
    
    try:
        decode_jwt(expired_token, secret)
        assert False, "JWT decoder accepted expired token"
    except ValueError as e:
        assert "Token has expired" in str(e), f"Unexpected expiration error: {e}"
    print("OK: JWT token expiration validation works.")

def run_integration_tests():
    print("--- Running API Integration Tests ---")
    
    # Enable auth requirements (disable development bypass)
    old_bypass = Config.DEVELOPMENT_BYPASS_AUTH
    Config.DEVELOPMENT_BYPASS_AUTH = False
    
    try:
        # Seed test user if needed
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Insert admin test user if not exists
        cursor.execute("SELECT id FROM users WHERE username = 'admin';")
        admin_row = cursor.fetchone()
        if not admin_row:
            admin_pass_hash = hash_password("AdminPassword123")
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES ('admin', 'admin@copyrightcenter.local', ?, 'Admin');
            """, (admin_pass_hash,))
            conn.commit()
            
        # Add a guest test user for testing role permissions
        cursor.execute("SELECT id FROM users WHERE username = 'guest_test';")
        guest_row = cursor.fetchone()
        if not guest_row:
            guest_pass_hash = hash_password("GuestPassword123")
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, role)
                VALUES ('guest_test', 'guest@copyrightcenter.local', ?, 'Guest');
            """, (guest_pass_hash,))
            conn.commit()
            
        conn.close()
        
        # 1. Login flow
        login_res = client.post("/api/v1/auth/login", json={
            "email": "admin",
            "password": "AdminPassword123"
        })
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        login_data = login_res.json()
        assert "token" in login_data, "Token missing in login response"
        admin_token = login_data["token"]
        print("OK: User login successfully returns token.")
        
        # Verify JWT payload format of the token
        payload = decode_jwt(admin_token, Config.SECRET_KEY)
        assert payload["username"] == "admin", "JWT username mismatch"
        assert payload["role"] == "Admin", "JWT role mismatch"
        print("OK: Returned token is a valid signed JWT.")
        
        # Login Guest user
        guest_login_res = client.post("/api/v1/auth/login", json={
            "email": "guest_test",
            "password": "GuestPassword123"
        })
        assert guest_login_res.status_code == 200
        guest_token = guest_login_res.json()["token"]
        print("OK: Guest user login successful.")
        
        # 2. Access protected endpoint (roles/me) with token
        me_res = client.get("/api/v1/auth/roles/me", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert me_res.status_code == 200, f"roles/me failed: {me_res.text}"
        me_data = me_res.json()
        assert me_data["username"] == "admin", "Incorrect username returned"
        assert me_data["role"] == "Admin", "Incorrect role returned"
        print("OK: Accessing protected endpoints with valid JWT works.")
        
        # Access with missing header
        me_no_auth = client.get("/api/v1/auth/roles/me")
        assert me_no_auth.status_code == 401, "Allowed access without auth header"
        print("OK: Missing auth header blocked with 401.")
        
        # Access with tampered JWT
        me_tampered = client.get("/api/v1/auth/roles/me", headers={
            "Authorization": f"Bearer {admin_token}abc"
        })
        assert me_tampered.status_code == 401, "Allowed access with tampered JWT"
        print("OK: Tampered JWT signature blocked with 401.")
        
        # 3. Role-based restrictions check
        # Admin action: register a user.
        # Check that Admin can access register user
        reg_res = client.post("/api/v1/auth/register", json={
            "username": f"new_editor_{int(time.time())}",
            "email": f"editor_{int(time.time())}@copyrightcenter.com",
            "password": "EditorPassword123",
            "role": "Editor"
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert reg_res.status_code == 201, f"Admin registration failed: {reg_res.text}"
        print("OK: Admin user can perform Admin-role restricted registration.")
        
        # Check that Guest user CAN perform registration (now public)
        reg_guest_res = client.post("/api/v1/auth/register", json={
            "username": f"bad_editor_{int(time.time())}",
            "email": f"bad_editor_{int(time.time())}@copyrightcenter.com",
            "password": "EditorPassword123",
            "role": "Editor"
        }, headers={"Authorization": f"Bearer {guest_token}"})
        assert reg_guest_res.status_code == 201, f"Guest registration failed: {reg_guest_res.text}"
        print("OK: Public user registration allowed.")
        
        # 4. Corrected Reports Router path check
        # Verify that reports route has prefix /api/v1/reports
        # Fetch report (using dummy/invalid ID 99999).
        # We expect a database 404 error ("Report not found" or "Case not found") from the reports.py route,
        # but NOT a FastAPI routing 404 (detail: "Not Found") from the router mismatch.
        reports_res = client.delete("/api/v1/reports/99999", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        # If it matches router, it will return 404 "Report not found" or similar detail
        assert reports_res.status_code == 404, f"Reports lookup returned unexpected status: {reports_res.status_code}"
        assert reports_res.json().get("detail") == "Report not found", f"Unexpected details response: {reports_res.json()}"
        print("OK: Reports endpoints correctly prefixed under /api/v1/reports.")
        
        # Verify that old /api/reports prefix returns 404 Router mismatch (Not Found)
        old_reports_res = client.get("/api/reports/99999", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert old_reports_res.status_code == 404, f"Old route did not return 404: {old_reports_res.status_code}"
        assert old_reports_res.json().get("detail") == "Not Found", f"Unexpected old path detail: {old_reports_res.json()}"
        print("OK: Old reports endpoint path /api/reports correctly deprecated and deactivated.")
        
        # 5. Logout verification
        logout_res = client.post("/api/v1/auth/logout", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert logout_res.status_code == 200, f"Logout failed: {logout_res.text}"
        print("OK: Logout successful.")
        
        # Verify that logged out JWT is no longer active in database and fails validation
        me_after_logout = client.get("/api/v1/auth/roles/me", headers={
            "Authorization": f"Bearer {admin_token}"
        })
        assert me_after_logout.status_code == 401, "Allowed session after logout"
        print("OK: Logged out JWT session correctly invalidated and rejected.")
        
    finally:
        Config.DEVELOPMENT_BYPASS_AUTH = old_bypass

if __name__ == "__main__":
    try:
        run_unit_tests()
        run_integration_tests()
        print("\nALL PHASE 1 TESTS PASSED SUCCESSFULLY! OK.")
        sys.exit(0)
    except AssertionError as e:
        print(f"\nTEST FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED EXCEPTION DURING TESTS: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
