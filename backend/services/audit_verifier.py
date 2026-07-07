import hashlib
import logging
from backend.database import get_db_connection

logger = logging.getLogger("tsn.audit_verifier")

class AuditVerifier:
    @staticmethod
    def compute_local_hash(user_id, action, entity_type, entity_id, details_json, prev_hash, created_at) -> str:
        """Helper to recompute log block hash locally in Python."""
        u_id = str(user_id) if user_id is not None else ""
        act = str(action) if action is not None else ""
        e_type = str(entity_type) if entity_type is not None else ""
        e_id = str(entity_id) if entity_id is not None else ""
        det = str(details_json) if details_json is not None else ""
        p_hash = str(prev_hash) if prev_hash is not None else "GENESIS"
        cat = str(created_at) if created_at is not None else ""
        
        data = f"{u_id}|{act}|{e_type}|{e_id}|{det}|{p_hash}|{cat}"
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    @staticmethod
    def verify_chain() -> tuple[bool, str]:
        """
        Loops through all audit logs and verifies the integrity of the hash chain.
        Returns:
            tuple (success, message)
        """
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, user_id, action, entity_type, entity_id, details_json, previous_entry_hash, entry_hash, created_at
                FROM audit_logs
                ORDER BY id ASC;
            """)
            rows = cursor.fetchall()
            
            if not rows:
                return True, "No logs recorded yet."
                
            prev_computed_hash = "GENESIS"
            for i, r in enumerate(rows):
                log_id = r["id"]
                recorded_prev_hash = r["previous_entry_hash"]
                recorded_entry_hash = r["entry_hash"]
                
                # Check link to previous block
                if recorded_prev_hash != prev_computed_hash:
                    err_msg = f"Chain link broken at log ID {log_id}. Expected previous hash '{prev_computed_hash}', got '{recorded_prev_hash}'."
                    logger.error(err_msg)
                    return False, err_msg
                    
                # Recompute hash for current block
                computed_hash = AuditVerifier.compute_local_hash(
                    user_id=r["user_id"],
                    action=r["action"],
                    entity_type=r["entity_type"],
                    entity_id=r["entity_id"],
                    details_json=r["details_json"],
                    prev_hash=recorded_prev_hash,
                    created_at=r["created_at"]
                )
                
                if computed_hash != recorded_entry_hash:
                    err_msg = f"Hash signature mismatch at log ID {log_id}. Computed '{computed_hash}', recorded '{recorded_entry_hash}'."
                    logger.error(err_msg)
                    return False, err_msg
                    
                prev_computed_hash = recorded_entry_hash
                
            return True, "Integrity verified successfully."
        finally:
            conn.close()
