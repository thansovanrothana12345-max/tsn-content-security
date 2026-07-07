import logging
from backend.database import get_db_connection

logger = logging.getLogger("tsn.copyright_enforcement")

class CopyrightEnforcementService:
    @staticmethod
    def log_takedown(evidence_id: int, recipient_platform: str, action_taken: str, status: str = "Draft", legal_signee: str = None) -> int:
        """Inserts an enforcement takedown notice audit log entry in the database."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Verify evidence exists
            cursor.execute("SELECT id FROM evidence WHERE id = ?;", (evidence_id,))
            if not cursor.fetchone():
                raise ValueError(f"Evidence reference not found with ID {evidence_id}")
                
            cursor.execute("""
                INSERT INTO takedown_logs (evidence_id, recipient_platform, action_taken, status, legal_signee, sent_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (evidence_id, recipient_platform, action_taken, status, legal_signee))
            log_id = cursor.lastrowid
            conn.commit()
            return log_id
        finally:
            conn.close()

    @staticmethod
    def get_takedown_history(evidence_id: int) -> list:
        """Fetches the complete takedown logs and status updates for a specific evidence ID."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, evidence_id, recipient_platform, action_taken, status, legal_signee, sent_at, updated_at
                FROM takedown_logs
                WHERE evidence_id = ?
                ORDER BY sent_at DESC, id DESC;
            """, (evidence_id,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def update_takedown_status(log_id: int, new_status: str) -> bool:
        """Transitions status of a logged takedown notice."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM takedown_logs WHERE id = ?;", (log_id,))
            if not cursor.fetchone():
                raise ValueError(f"Takedown log not found with ID {log_id}")
                
            cursor.execute("""
                UPDATE takedown_logs 
                SET status = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?;
            """, (new_status, log_id))
            conn.commit()
            return True
        finally:
            conn.close()
