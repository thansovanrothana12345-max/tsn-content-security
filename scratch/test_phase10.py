import sys
import os
import logging

# Adjust Python path to allow backend imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.app import app

client = TestClient(app, raise_server_exceptions=False)

def run_phase10_tests():
    print("--- Running Phase 10 Production Compliance Tests ---")
    
    # 1. Test: Security Headers returned on root endpoint
    res = client.get("/")
    assert res.status_code == 200
    
    headers = res.headers
    assert headers.get("X-Content-Type-Options") == "nosniff", "Missing X-Content-Type-Options"
    assert headers.get("X-Frame-Options") == "DENY", "Missing X-Frame-Options"
    assert headers.get("X-XSS-Protection") == "1; mode=block", "Missing X-XSS-Protection"
    assert "Content-Security-Policy" in headers, "Missing Content-Security-Policy header"
    print("OK: Secure HTTP headers conformed and validated.")

    # 2. Test: Global Exception Handler catches unhandled errors and hides traces
    # We will trigger a fake route that intentionally throws an exception to check global boundary
    @app.get("/api/v1/test-intentional-crash-route-for-compliance")
    def trigger_intentional_crash():
        raise ValueError("Intentional compliance check error")
        
    crash_res = client.get("/api/v1/test-intentional-crash-route-for-compliance")
    assert crash_res.status_code == 500, f"Expected 500, got {crash_res.status_code}"
    
    body = crash_res.json()
    assert body == {"detail": "Internal server error"}, f"Expected hidden trace body, got {body}"
    print("OK: Global Exception boundary blocks sensitive trace disclosures.")

    # 3. Test: Rotating app log file populated on disk
    log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "storage", "logs", "app.log")
    assert os.path.exists(log_path), f"App log file missing at {log_path}"
    assert os.path.getsize(log_path) > 0, "App log file size is empty"
    
    # Confirm that the intentional crash was logged
    with open(log_path, "r", encoding="utf-8") as f:
        log_content = f.read()
        assert "Intentional compliance check error" in log_content, "Intentional crash exception trace was not logged"
        
    print("OK: Rotating app logging verified and active.")

if __name__ == "__main__":
    try:
        run_phase10_tests()
        print("\nALL PHASE 10 PRODUCTION COMPLIANCE TESTS PASSED SUCCESSFULLY! OK.")
        sys.exit(0)
    except AssertionError as e:
        print(f"\nTEST FAILURE: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"\nUNEXPECTED EXCEPTION DURING TESTS: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
