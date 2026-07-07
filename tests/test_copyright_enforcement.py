import unittest
import sys
import os

# Append project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db_connection, init_db
from backend.services.copyright_enforcement import CopyrightEnforcementService

class TestCopyrightEnforcement(unittest.TestCase):
    def setUp(self):
        init_db()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cases;")
        cursor.execute("DELETE FROM evidence;")
        cursor.execute("INSERT INTO cases (id, title, description, status, priority) VALUES (888, 'Case 888', 'Desc', 'Active', 'Medium');")
        cursor.execute("""
            INSERT INTO evidence (id, case_id, platform, url, title, uploader, upload_date, status)
            VALUES (202, 888, 'YouTube', 'http://infringe-url.com', 'Infringing Video', 'bad_user', '2026-07-07', 'Detected');
        """)
        conn.commit()
        conn.close()

    def test_enforcement_logs_registry_and_status(self):
        # 1. Log a takedown notice
        log_id = CopyrightEnforcementService.log_takedown(
            evidence_id=202,
            recipient_platform="YouTube",
            action_taken="DMCA Notice",
            status="Draft",
            legal_signee="Agent John"
        )
        self.assertIsNotNone(log_id)
        
        # 2. Get history and verify values
        history = CopyrightEnforcementService.get_takedown_history(202)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["status"], "Draft")
        self.assertEqual(history[0]["legal_signee"], "Agent John")
        
        # 3. Update status to Sent and verify
        success = CopyrightEnforcementService.update_takedown_status(log_id, "Sent")
        self.assertTrue(success)
        
        history = CopyrightEnforcementService.get_takedown_history(202)
        self.assertEqual(history[0]["status"], "Sent")

if __name__ == "__main__":
    unittest.main()
