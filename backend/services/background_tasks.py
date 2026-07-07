import concurrent.futures
import threading
import logging
import time
from backend.database import get_db_connection
from backend.config import Config

logger = logging.getLogger("tsn.background_tasks")

class BackgroundTaskManager:
    _instance = None

    def __init__(self, max_workers: int = 4):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="AIWorker")
        self.active_jobs = {}      # job_id -> future
        self.cancel_events = {}    # job_id -> threading.Event
        self.cancelled_jobs = set()
        self.lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def start_task(self, job_id: int, func, *args, **kwargs):
        """Starts a background job execution inside the thread pool."""
        with self.lock:
            if job_id in self.active_jobs:
                logger.warning(f"Job {job_id} is already running.")
                return
            
            cancel_event = threading.Event()
            self.cancel_events[job_id] = cancel_event
            
            future = self.executor.submit(self._run_wrapper, job_id, cancel_event, func, *args, **kwargs)
            self.active_jobs[job_id] = future
            logger.info(f"Enqueued job {job_id} into the background worker pool.")

    def cancel_job(self, job_id: int) -> bool:
        """Triggers cancellation event for a running job and updates database status."""
        logger.info(f"Requested cancellation for job {job_id}.")
        
        # 1. Update database
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE background_jobs SET status = 'Cancelled', current_step = 'Cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (job_id,)
            )
            cursor.execute(
                "UPDATE scan_jobs SET status = 'Cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (job_id,)
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Failed to update database status for cancel job {job_id}: {e}")
        finally:
            conn.close()

        # 2. Set memory cancellation event
        with self.lock:
            self.cancelled_jobs.add(job_id)
            if job_id in self.cancel_events:
                self.cancel_events[job_id].set()
            if job_id in self.active_jobs:
                self.active_jobs[job_id].cancel()
                return True
        return False

    def is_cancelled(self, job_id: int) -> bool:
        """Checks if a job has been cancelled either in-memory or in the database."""
        # 1. Check memory event
        with self.lock:
            if job_id in self.cancelled_jobs:
                return True
            if job_id in self.cancel_events and self.cancel_events[job_id].is_set():
                return True

        # 2. Check Database
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM background_jobs WHERE id = ? UNION ALL SELECT status FROM scan_jobs WHERE id = ? LIMIT 2;", (job_id, job_id))
            rows = cursor.fetchall()
            for r in rows:
                status_str = r[0] if isinstance(r, (tuple, list)) else r["status"]
                if status_str == "Cancelled":
                    with self.lock:
                        self.cancelled_jobs.add(job_id)
                        if job_id in self.cancel_events:
                            self.cancel_events[job_id].set()
                    return True
        except Exception:
            pass
        finally:
            conn.close()
            
        return False

    def _run_wrapper(self, job_id: int, cancel_event: threading.Event, func, *args, **kwargs):
        """Wraps task function to enforce timeouts and cleanup job handles on exit."""
        timeout = float(getattr(Config, "AI_INFERENCE_TIMEOUT", 120.0))
        
        # Enforce timeout inside a sub-future
        sub_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        sub_future = sub_executor.submit(func, *args, **kwargs)
        
        exception = None
        result = None
        
        try:
            poll_interval = min(0.05, timeout)
            elapsed = 0.0
            
            while elapsed < timeout:
                if cancel_event.is_set() or self.is_cancelled(job_id):
                    sub_future.cancel()
                    raise InterruptedError("Job cancelled by user.")
                
                try:
                    result = sub_future.result(timeout=poll_interval)
                    break
                except concurrent.futures.TimeoutError:
                    elapsed += poll_interval
            else:
                sub_future.cancel()
                raise TimeoutError(f"Job execution exceeded timeout of {timeout}s.")
                
        except Exception as e:
            exception = e
        finally:
            sub_executor.shutdown(wait=False)
            
            with self.lock:
                if job_id in self.active_jobs:
                    del self.active_jobs[job_id]
                if job_id in self.cancel_events:
                    del self.cancel_events[job_id]
                # Prune cancelled_jobs if it gets too large
                if len(self.cancelled_jobs) > 1000:
                    self.cancelled_jobs.clear()
            
            if exception:
                raise exception
            return result
