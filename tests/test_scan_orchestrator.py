import unittest
import sys
import os
import json
import time

# Append project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db_connection, init_db
from backend.services.scan_orchestrator import ScanOrchestrator
from backend.worker import execute_session_task

class TestScanOrchestrator(unittest.TestCase):
    def setUp(self):
        init_db()
        # Seed an active case to test sessions
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cases;")
        cursor.execute("INSERT INTO cases (id, title, description, status, priority) VALUES (999, 'Test Case', 'Desc', 'Active', 'Medium');")
        conn.commit()
        conn.close()

    def test_dag_dependency_execution_flow(self):
        session_data = ScanOrchestrator.create_session(case_id=999, created_by=1)
        session_uuid = session_data["session_uuid"]
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Fetch next schedulable task - should ONLY return the "upload" task
        # since all other tasks in the session depend on upstream tasks.
        cursor.execute("""
            SELECT t.id, t.task_type
            FROM scan_session_tasks t
            JOIN scan_sessions s ON t.session_id = s.id
            WHERE t.status = 'Pending'
              AND s.status IN ('Pending', 'Running')
              AND (
                  t.depends_on_task_uuid IS NULL
                  OR (
                      SELECT status FROM scan_session_tasks WHERE task_uuid = t.depends_on_task_uuid
                  ) = 'Completed'
              )
            ORDER BY t.id ASC
            LIMIT 1;
        """)
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["task_type"], "upload")
        
        # 2. Execute the upload task
        upload_task_id = row["id"]
        cursor.execute("SELECT session_id FROM scan_session_tasks WHERE id = ?;", (upload_task_id,))
        session_id = cursor.fetchone()["session_id"]
        
        execute_session_task(upload_task_id, session_id, "upload", {})
        
        # 3. Fetch next schedulable task - should now be "preprocess"
        # because "upload" is marked "Completed".
        cursor.execute("""
            SELECT t.id, t.task_type
            FROM scan_session_tasks t
            JOIN scan_sessions s ON t.session_id = s.id
            WHERE t.status = 'Pending'
              AND s.status IN ('Pending', 'Running')
              AND (
                  t.depends_on_task_uuid IS NULL
                  OR (
                      SELECT status FROM scan_session_tasks WHERE task_uuid = t.depends_on_task_uuid
                  ) = 'Completed'
              )
            ORDER BY t.id ASC
            LIMIT 1;
        """)
        row2 = cursor.fetchone()
        self.assertIsNotNone(row2)
        self.assertEqual(row2["task_type"], "preprocess")
        
        # 4. Confirm progress percent is updated
        progress = ScanOrchestrator.get_session_progress(session_uuid)
        # 1 out of 7 completed -> ~14.29%
        self.assertGreater(progress["progress_percent"], 14.0)
        self.assertLess(progress["progress_percent"], 15.0)
        
        conn.close()

if __name__ == "__main__":
    unittest.main()
