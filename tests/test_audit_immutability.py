import unittest
import sys
import os

# Append project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db_connection, init_db
from backend.services.audit_verifier import AuditVerifier

class TestAuditImmutability(unittest.TestCase):
    def setUp(self):
        init_db()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM audit_logs;")
        conn.commit()
        conn.close()

    def test_audit_logs_cryptographic_chain(self):
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Insert 3 logs
        cursor.execute("INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json) VALUES (1, 'CREATE', 'case', 101, '{}');")
        cursor.execute("INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json) VALUES (1, 'UPDATE', 'case', 101, '{\"modified\": true}');")
        cursor.execute("INSERT INTO audit_logs (user_id, action, entity_type, entity_id, details_json) VALUES (2, 'DELETE', 'case', 101, '{}');")
        conn.commit()
        
        # 2. Verify audit verifier validates this clean chain
        success, msg = AuditVerifier.verify_chain()
        self.assertTrue(success)
        self.assertEqual(msg, "Integrity verified successfully.")
        
        # 3. Simulate tampering: update the action on one of the log rows directly in the database
        cursor.execute("UPDATE audit_logs SET action = 'UPDATE_TAMPERED' WHERE id = (SELECT MIN(id) + 1 FROM audit_logs);")
        conn.commit()
        
        # 4. Verify verifier catches this gap
        success_tampered, msg_tampered = AuditVerifier.verify_chain()
        self.assertFalse(success_tampered)
        self.assertIn("Hash signature mismatch", msg_tampered)
        
        conn.close()

if __name__ == "__main__":
    unittest.main()
