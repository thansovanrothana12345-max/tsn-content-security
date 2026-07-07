import sys
import os
import time

# Adjust Python path to allow backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app)

def test_endpoints():
    print("--- Verifying Public Endpoints ---")
    
    # 1. Test POST /api/v1/auth/register (unauthenticated / public)
    unique_username = f"public_user_{int(time.time())}"
    unique_email = f"public_user_{int(time.time())}@example.com"
    
    print(f"Registering public user '{unique_username}' without token...")
    reg_res = client.post("/api/v1/auth/register", json={
        "username": unique_username,
        "email": unique_email,
        "password": "PublicPassword123",
        "role": "Guest"
    })
    
    print(f"Response status: {reg_res.status_code}")
    print(f"Response body: {reg_res.text}")
    assert reg_res.status_code == 201, f"Expected 201 Created, got {reg_res.status_code}"
    
    # 2. Test POST /api/v1/auth/login
    print("Logging in with the newly registered user...")
    login_res = client.post("/api/v1/auth/login", json={
        "email": unique_username,
        "password": "PublicPassword123"
    })
    print(f"Response status: {login_res.status_code}")
    assert login_res.status_code == 200, f"Expected 200 OK, got {login_res.status_code}"
    
    # 3. Test GET /docs
    print("Requesting Swagger docs /docs...")
    docs_res = client.get("/docs")
    print(f"Response status: {docs_res.status_code}")
    assert docs_res.status_code == 200, f"Expected 200 OK, got {docs_res.status_code}"
    
    print("\nALL LOCAL INTEGRATION ENDPOINT CHECKS PASSED SUCCESSFULLY! OK.")

if __name__ == "__main__":
    try:
        test_endpoints()
        sys.exit(0)
    except AssertionError as e:
        print(f"\nTEST FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED EXCEPTION DURING TESTS: {e}", file=sys.stderr)
        sys.exit(1)
