from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from backend.routes.auth import get_current_user
from backend.database import get_db_connection

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])

class NotificationItem(BaseModel):
    id: int
    user_id: Optional[int]
    title: str
    message: str
    is_read: int
    created_at: str

@router.get("", response_model=List[NotificationItem])
def list_notifications(user: dict = Depends(get_current_user)):
    """Retrieves all notifications for the current authenticated user."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, user_id, title, message, is_read, created_at 
            FROM notifications 
            ORDER BY created_at DESC;
        """)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

@router.post("/{notification_id}/read")
def mark_as_read(notification_id: int, user: dict = Depends(get_current_user)):
    """Marks a specific notification as read."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM notifications WHERE id = ?;", (notification_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Notification not found.")
        
        cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ?;", (notification_id,))
        conn.commit()
        return {"success": True, "message": "Notification marked as read."}
    finally:
        conn.close()

@router.post("/read-all")
def mark_all_as_read(user: dict = Depends(get_current_user)):
    """Marks all notifications for the current user as read."""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE notifications SET is_read = 1;")
        conn.commit()
        return {"success": True, "message": "All notifications marked as read."}
    finally:
        conn.close()
