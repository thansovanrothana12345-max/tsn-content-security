import unittest
import sys
import os
import time
import sqlite3

# Append project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import Config
from backend.database import get_db_connection, init_db
from backend.fingerprint import JobsQueueService
from backend.services.model_manager import ModelLifecycleManager
from backend.worker import update_worker_heartbeat

class TestUnifiedPollingAndHeartbeats(unittest.TestCase):
    def setUp(self):
        init_db()

    def test_jobs_queue_priority_order(self):
        # Clear existing jobs in queue
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM jobs_queue;")
        conn.commit()
        
        service = JobsQueueService()
        
        # Enqueue low priority job
        service.enqueue_job(conn, case_id=1, evidence_id=None, job_type="reindex", payload={"task": "low"}, priority=1)
        # Enqueue high priority job
        service.enqueue_job(conn, case_id=1, evidence_id=None, job_type="leak_scan", payload={"task": "high"}, priority=4)
        # Enqueue medium priority job
        service.enqueue_job(conn, case_id=1, evidence_id=None, job_type="asset_ingestion", payload={"task": "medium"}, priority=2)
        
        # Fetch first job - should be the high priority one (priority=4)
        job1 = service.fetch_next_job(conn)
        self.assertIsNotNone(job1)
        self.assertEqual(job1["job_type"], "leak_scan")
        self.assertEqual(job1["priority"], 4)
        
        # Fetch second job - should be medium priority (priority=2)
        job2 = service.fetch_next_job(conn)
        self.assertIsNotNone(job2)
        self.assertEqual(job2["job_type"], "asset_ingestion")
        self.assertEqual(job2["priority"], 2)
        
        # Fetch third job - should be low priority (priority=1)
        job3 = service.fetch_next_job(conn)
        self.assertIsNotNone(job3)
        self.assertEqual(job3["job_type"], "reindex")
        self.assertEqual(job3["priority"], 1)
        
        # Fetch fourth job - should be None
        job4 = service.fetch_next_job(conn)
        self.assertIsNone(job4)
        conn.close()

    def test_model_lifecycle_idle_unload(self):
        manager = ModelLifecycleManager.get_instance()
        provider = manager.get_provider("sentence_transformers")
        
        # Ensure model is loaded
        provider.load()
        self.assertTrue(provider.is_loaded())
        
        # Mark as last used 20 seconds ago and set timeout to 10 seconds
        provider.last_used = time.time() - 20.0
        Config.AI_MODEL_IDLE_TIMEOUT = 10.0
        
        # Unload idle models
        manager.unload_idle_models()
        self.assertFalse(provider.is_loaded())

    def test_worker_heartbeat_updates(self):
        worker_id = "test_worker_123"
        update_worker_heartbeat(worker_id, status="Idle", active_job_id=99, active_job_type="scan_link")
        
        # Verify it is in database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT status, active_job_id, active_job_type FROM worker_heartbeats WHERE worker_id = ?;", (worker_id,))
        row = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertEqual(row["status"], "Idle")
        self.assertEqual(row["active_job_id"], 99)
        self.assertEqual(row["active_job_type"], "scan_link")

if __name__ == "__main__":
    unittest.main()
