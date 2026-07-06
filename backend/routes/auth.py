from fastapi import APIRouter, HTTPException, Depends, Header
from pydantic import BaseModel, EmailStr
from typing import Optional
import sqlite3
import secrets
import base64
import json
import hmac
import hashlib
import time
from datetime import datetime, timedelta
from backend.database import get_db_connection, hash_password, verify_password
from backend.config import Config

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])
router_v2 = APIRouter(prefix="/api/auth", tags=["Authentication"])

def base64url_encode(payload: bytes) -> str:
    return base64.urlsafe_b64encode(payload).replace(b'=', b'').decode('utf-8')

def base64url_decode(payload: str) -> bytes:
    padding = '=' * (4 - len(payload) % 4)
    return base64.urlsafe_b64decode(payload + padding)

def encode_jwt(payload: dict, secret: str) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    header_b64 = base64url_encode(json.dumps(header).encode('utf-8'))
    payload_b64 = base64url_encode(json.dumps(payload).encode('utf-8'))
    
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
    signature_b64 = base64url_encode(signature)
    
    return f"{header_b64}.{payload_b64}.{signature_b64}"

def decode_jwt(token: str, secret: str) -> dict:
    try:
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid token format")
        
        header_b64, payload_b64, signature_b64 = parts
        
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_signature = hmac.new(secret.encode('utf-8'), signing_input, hashlib.sha256).digest()
        expected_signature_b64 = base64url_encode(expected_signature)
        
        if not hmac.compare_digest(signature_b64, expected_signature_b64):
            raise ValueError("Signature verification failed")
            
        payload = json.loads(base64url_decode(payload_b64).decode('utf-8'))
        
        if "exp" in payload and payload["exp"] < time.time():
            raise ValueError("Token has expired")
            
        return payload
    except Exception as e:
        if isinstance(e, ValueError):
            raise e
        raise ValueError(f"Invalid token: {str(e)}")

class LoginRequest(BaseModel):
    email: str
    password: str

class UserDetail(BaseModel):
    id: int
    username: str
    email: str
    role: str

class LoginResponse(BaseModel):
    success: bool
    user: UserDetail
    token: str
    expires_at: str

class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str # 'Admin', 'Editor', 'Reviewer', 'Guest'

def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        if Config.DEVELOPMENT_BYPASS_AUTH:
            conn = get_db_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT id, username, email, role FROM users WHERE username = 'admin';")
                user = cursor.fetchone()
                if user:
                    return {
                        "id": user["id"],
                        "username": user["username"],
                        "email": user["email"],
                        "role": user["role"]
                    }
            finally:
                conn.close()
        raise HTTPException(
            status_code=401, 
            detail={"error": "UNAUTHORIZED", "message": "Authentication token expired or missing."}
        )
    token = authorization.split(" ")[1]
    
    try:
        payload = decode_jwt(token, Config.SECRET_KEY)
    except ValueError as e:
        raise HTTPException(
            status_code=401, 
            detail={"error": "UNAUTHORIZED", "message": f"Session token has expired or is invalid: {str(e)}"}
        )
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Check that session is still active in the database (for stateful logouts)
        cursor.execute("""
            SELECT s.user_id FROM sessions s 
            WHERE s.token = ? AND s.expires_at > ?
        """, (token, datetime.utcnow().isoformat()))
        session = cursor.fetchone()
        
        if not session:
            raise HTTPException(
                status_code=401, 
                detail={"error": "UNAUTHORIZED", "message": "Session token has expired or is invalid."}
            )
            
        # Query user details from DB to ensure integrity (email etc.)
        cursor.execute("SELECT id, username, email, role FROM users WHERE id = ?", (payload["id"],))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(
                status_code=401, 
                detail={"error": "UNAUTHORIZED", "message": "User not found."}
            )
            
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"]
        }
    finally:
        conn.close()

def require_role(allowed_roles: list[str]):
    def dependency(user: dict = Depends(get_current_user)):
        if user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=403, 
                detail={"error": "FORBIDDEN", "message": "You do not have permission to execute this action."}
            )
        return user
    return dependency

# 1. Login Endpoint
def process_login(request: LoginRequest):
    print(f"[AUTH] Login attempt received for email/username: '{request.email}'")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Query user (case-insensitively for stability)
        cursor.execute("""
            SELECT id, username, email, password_hash, role 
            FROM users 
            WHERE LOWER(email) = LOWER(?) OR LOWER(username) = LOWER(?)
        """, (request.email, request.email))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            print(f"[AUTH] Login failed for '{request.email}': user not found")
            raise HTTPException(
                status_code=401, 
                detail={"error": "UNAUTHORIZED", "message": "Invalid email/username or password."}
            )
            
        # Verify hashed password with bcrypt verify_password
        if not verify_password(request.password, user["password_hash"]):
            conn.close()
            print(f"[AUTH] Login failed for '{request.email}': wrong password")
            raise HTTPException(
                status_code=401, 
                detail={"error": "UNAUTHORIZED", "message": "Invalid email/username or password."}
            )
            
        # Create session token as JWT
        exp_seconds = int((datetime.utcnow() + timedelta(hours=Config.SESSION_EXPIRE_HOURS)).timestamp())
        payload = {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "exp": exp_seconds
        }
        token = encode_jwt(payload, Config.SECRET_KEY)
        expires_at = (datetime.utcnow() + timedelta(hours=Config.SESSION_EXPIRE_HOURS)).isoformat()
        
        cursor.execute("""
            INSERT INTO sessions (user_id, token, expires_at)
            VALUES (?, ?, ?)
        """, (user["id"], token, expires_at))
        
        # Log audit event
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
            VALUES (?, 'LOGIN', 'user', ?, ?)
        """, (user["id"], user["id"], '{"message": "User logged in successfully."}'))
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "role": user["role"]
            },
            "token": token,
            "expires_at": expires_at
        }
    except sqlite3.Error as e:
        if conn:
            conn.close()
        print(f"[AUTH] Login database error for '{request.email}': {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={"error": "INTERNAL_SERVER_ERROR", "message": f"Database error during authentication: {str(e)}"}
        )
    except Exception as e:
        if conn:
            conn.close()
        raise e

@router.post("/login", response_model=LoginResponse)
def login_legacy(request: LoginRequest):
    return process_login(request)

@router_v2.post("/login", response_model=LoginResponse)
def login_pro(request: LoginRequest):
    return process_login(request)

# 2. Logout Endpoint
@router.post("/logout")
def logout(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=400, detail="Authorization header missing or invalid format")
    token = authorization.split(" ")[1]
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Get active session user
        cursor.execute("SELECT user_id FROM sessions WHERE token = ?", (token,))
        session = cursor.fetchone()
        
        if session:
            cursor.execute("DELETE FROM sessions WHERE token = ?", (token,))
            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
                VALUES (?, 'LOGOUT', 'user', ?, '{"message": "User logged out successfully."}')
            """, (session["user_id"], session["user_id"]))
            conn.commit()
    finally:
        conn.close()
    return {"message": "Logged out successfully."}

# 3. Registration Endpoint (Admin only)
@router.post("/register", status_code=201)
def register(request: RegisterRequest, admin_user: dict = Depends(require_role(["Admin"]))):
    if request.role not in ["Admin", "Editor", "Reviewer", "Guest"]:
        raise HTTPException(
            status_code=400, 
            detail={"error": "BAD_REQUEST", "message": "Invalid user role specified."}
        )
        
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        # Check uniqueness
        cursor.execute("SELECT id FROM users WHERE username = ? OR email = ?", (request.username, request.email))
        if cursor.fetchone():
            raise HTTPException(
                status_code=400, 
                detail={"error": "BAD_REQUEST", "message": "Username or email already exists."}
            )
            
        new_pass_hash = hash_password(request.password)
        cursor.execute("""
            INSERT INTO users (username, email, password_hash, role)
            VALUES (?, ?, ?, ?)
        """, (request.username, request.email, new_pass_hash, request.role))
        new_user_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json)
            VALUES (?, 'REGISTER_USER', 'user', ?, ?)
        """, (admin_user["id"], new_user_id, f'{{"created_user": "{request.username}", "role": "{request.role}"}}'))
        
        conn.commit()
    except sqlite3.Error as e:
        raise HTTPException(status_code=500, detail=f"Database write error: {str(e)}")
    finally:
        conn.close()
    return {"message": f"User {request.username} successfully registered with role {request.role}."}

@router.get("/users")
def list_system_users(user: dict = Depends(get_current_user)):
    """Lists all registered system users (username, email, role)."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, email, role FROM users ORDER BY username ASC;")
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

# 4. Check Current User Role scopes
@router.get("/roles/me")
def get_my_role(user: dict = Depends(get_current_user)):
    """Returns the authenticated user details and active role permissions."""
    return user

# 5. Get Paginated System Audit Logs (Admin only)
@router.get("/audit/logs")
def get_system_audit_logs(
    limit: int = 50,
    offset: int = 0,
    action: Optional[str] = None,
    admin_user: dict = Depends(require_role(["Admin"]))
):
    """Retrieves paginated, read-only system audit trails logs history."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        
        query = "SELECT id, user_id, action, entity_type, entity_id, details_json, ip_address, created_at FROM audit_logs"
        params = []
        
        if action:
             query += " WHERE action = ?"
             params.append(action)
             
        query += " ORDER BY id DESC LIMIT ? OFFSET ?;"
        params.extend([limit, offset])
        
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

