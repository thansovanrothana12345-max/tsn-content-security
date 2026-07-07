import httpx
import sys
import os

BASE_URL = "http://127.0.0.1:8000"

def run_test():
    client = httpx.Client(base_url=BASE_URL)
    
    # 1. Login
    login_res = client.post("/api/v1/auth/login", json={
        "email": "admin",
        "password": "AdminPassword123"
    })
    
    if login_res.status_code != 200:
        print("Login failed:", login_res.status_code, login_res.text)
        sys.exit(1)
        
    token = login_res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Logged in successfully. Token obtained.")
    
    # 2. Create case
    case_res = client.post("/api/v1/cases", headers=headers, json={
        "title": "Case for Upload Test",
        "description": "reproduction case",
        "priority": "Medium",
        "client_name": "Test Client",
        "platform": "Other"
    })
    
    if case_res.status_code != 201:
        print("Case creation failed:", case_res.status_code, case_res.text)
        sys.exit(1)
        
    case_id = case_res.json()["id"]
    print(f"Created Case ID: {case_id}")
    
    # Create test dummy data
    dummy_data = b"dummy jpeg data"
    
    # Test 1: Upload lowercase extension (.jpg)
    print("\n--- TEST 1: Uploading lowercase extension (.jpg) ---")
    files_jpg = {"file": ("test_evidence.jpg", dummy_data, "image/jpeg")}
    try:
        res_jpg = client.post(f"/api/v1/evidence/upload/{case_id}", headers=headers, files=files_jpg)
        print("Request URL:", res_jpg.request.url)
        print("Request Headers:", res_jpg.request.headers)
        print("Response Status Code:", res_jpg.status_code)
        print("Response Body:", res_jpg.json())
    except Exception as e:
        print("Test 1 failed with exception:", e)
        
    # Test 2: Upload uppercase extension (.JPG)
    print("\n--- TEST 2: Uploading uppercase extension (.JPG) ---")
    files_JPG = {"file": ("test_evidence.JPG", dummy_data, "image/jpeg")}
    try:
        res_JPG = client.post(f"/api/v1/evidence/upload/{case_id}", headers=headers, files=files_JPG)
        print("Request URL:", res_JPG.request.url)
        print("Request Headers:", res_JPG.request.headers)
        print("Response Status Code:", res_JPG.status_code)
        print("Response Body:", res_JPG.json())
    except Exception as e:
        print("Test 2 failed with exception:", e)

if __name__ == "__main__":
    run_test()
