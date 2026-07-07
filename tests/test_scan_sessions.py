import unittest
import sys
import os

# Append project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db_connection, init_db
from backend.services.scan_orchestrator import ScanOrchestrator

class TestScanSessions(unittest.TestCase):
    def setUp(self):
        init_db()
        # Seed an active case to test sessions
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cases;")
        cursor.execute("INSERT INTO cases (id, title, description, status, priority) VALUES (999, 'Test Case', 'Desc', 'Active', 'Medium');")
        conn.commit()
        conn.close()

    def test_session_lifecycle_transitions(self):
        # 1. Create session
        session_data = ScanOrchestrator.create_session(case_id=999, created_by=1)
        session_uuid = session_data["session_uuid"]
        self.assertIsNotNone(session_uuid)
        
        # 2. Get progress (should be Pending and 0%)
        progress = ScanOrchestrator.get_session_progress(session_uuid)
        self.assertEqual(progress["status"], "Pending")
        self.assertEqual(progress["progress_percent"], 0.0)
        self.assertEqual(len(progress["tasks"]), 7)
        
        # 3. Try to pause session - should transition to Paused
        paused = ScanOrchestrator.pause_session(session_uuid)
        self.assertTrue(paused)
        progress = ScanOrchestrator.get_session_progress(session_uuid)
        self.assertEqual(progress["status"], "Paused")
        
        # 4. Try to resume session - should transition to Running/Pending
        resumed = ScanOrchestrator.resume_session(session_uuid)
        self.assertTrue(resumed)
        progress = ScanOrchestrator.get_session_progress(session_uuid)
        self.assertEqual(progress["status"], "Running")
        
        # 5. Try to cancel session - should transition to Cancelled
        cancelled = ScanOrchestrator.cancel_session(session_uuid)
        self.assertTrue(cancelled)
        progress = ScanOrchestrator.get_session_progress(session_uuid)
        self.assertEqual(progress["status"], "Cancelled")
        
        # 6. Try to retry session - should transition back to Pending
        retried = ScanOrchestrator.retry_session(session_uuid)
        self.assertTrue(retried)
        progress = ScanOrchestrator.get_session_progress(session_uuid)
        self.assertEqual(progress["status"], "Pending")

if __name__ == "__main__":
    unittest.main()
