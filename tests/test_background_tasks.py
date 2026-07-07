import unittest
import sys
import os
import time
import threading
from unittest.mock import patch, MagicMock

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.background_tasks import BackgroundTaskManager
from backend.config import Config

class TestBackgroundTasks(unittest.TestCase):
    def setUp(self):
        self.manager = BackgroundTaskManager(max_workers=2)

    def test_concurrent_execution(self):
        execution_order = []
        lock = threading.Lock()

        def slow_task(name, sleep_duration):
            time.sleep(sleep_duration)
            with lock:
                execution_order.append(name)

        self.manager.start_task(101, slow_task, "task_1", 0.2)
        self.manager.start_task(102, slow_task, "task_2", 0.05)

        time.sleep(0.3)
        self.assertEqual(execution_order, ["task_2", "task_1"])

    @patch("backend.services.background_tasks.Config")
    def test_timeout_enforcement(self, mock_config):
        mock_config.AI_INFERENCE_TIMEOUT = 0.1

        def hanging_task():
            time.sleep(1.0)
            return "finished"

        self.manager.start_task(103, hanging_task)
        time.sleep(0.3)
        self.assertNotIn(103, self.manager.active_jobs)

    @patch("backend.services.background_tasks.get_db_connection")
    def test_task_cancellation(self, mock_db):
        mock_conn = MagicMock()
        mock_db.return_value = mock_conn

        task_was_interrupted = False

        def cancellable_task(job_id):
            nonlocal task_was_interrupted
            for _ in range(20):
                if self.manager.is_cancelled(job_id):
                    task_was_interrupted = True
                    raise InterruptedError("Cancelled")
                time.sleep(0.05)

        self.manager.start_task(104, cancellable_task, 104)
        time.sleep(0.1)
        self.manager.cancel_job(104)
        time.sleep(0.2)

        self.assertTrue(task_was_interrupted)
        self.assertNotIn(104, self.manager.active_jobs)

if __name__ == "__main__":
    unittest.main()
