import uuid
import json
import logging
from backend.database import get_db_connection

logger = logging.getLogger("tsn.scan_orchestrator")

class ScanOrchestrator:
    @staticmethod
    def create_session(case_id: int, created_by: int = None) -> dict:
        """Initializes a new scan session and populates its DAG sub-tasks."""
        session_uuid = str(uuid.uuid4())
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Verify case exists
            cursor.execute("SELECT id FROM cases WHERE id = ? AND is_deleted = 0;", (case_id,))
            if not cursor.fetchone():
                raise ValueError(f"Active case not found with ID {case_id}")

            # 1. Insert scan session
            cursor.execute("""
                INSERT INTO scan_sessions (session_uuid, case_id, status, progress_percent, created_by)
                VALUES (?, ?, 'Pending', 0.0, ?);
            """, (session_uuid, case_id, created_by))
            session_id = cursor.lastrowid

            # 2. Define 7-stage DAG task template
            task_types = [
                ('upload', None),
                ('preprocess', 'upload'),
                ('fingerprint', 'preprocess'),
                ('search', 'fingerprint'),
                ('ai_detect', 'search'),
                ('collect_evidence', 'ai_detect'),
                ('reporting', 'collect_evidence')
            ]
            
            task_uuids = {}
            for t_type, _ in task_types:
                task_uuids[t_type] = str(uuid.uuid4())

            for t_type, dep_type in task_types:
                t_uuid = task_uuids[t_type]
                dep_uuid = task_uuids[dep_type] if dep_type else None
                
                cursor.execute("""
                    INSERT INTO scan_session_tasks (session_id, task_uuid, task_type, status, depends_on_task_uuid, payload_json)
                    VALUES (?, ?, ?, 'Pending', ?, '{}');
                """, (session_id, t_uuid, t_type, dep_uuid))

            conn.commit()
            
            return {
                "session_uuid": session_uuid,
                "case_id": case_id,
                "status": "Pending",
                "progress_percent": 0.0,
                "tasks": task_uuids
            }
        finally:
            conn.close()

    @staticmethod
    def pause_session(session_uuid: str) -> bool:
        """Transitions scan session and its Pending tasks to Paused."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, status FROM scan_sessions WHERE session_uuid = ?;", (session_uuid,))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Scan session not found.")
            
            session_id = row["id"]
            current_status = row["status"]
            
            if current_status not in ("Pending", "Running"):
                return False
                
            cursor.execute("UPDATE scan_sessions SET status = 'Paused', updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (session_id,))
            cursor.execute("""
                UPDATE scan_session_tasks 
                SET status = 'Paused', updated_at = CURRENT_TIMESTAMP 
                WHERE session_id = ? AND status = 'Pending';
            """, (session_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def resume_session(session_uuid: str) -> bool:
        """Resumes a paused session, returning Paused tasks to Pending."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, status FROM scan_sessions WHERE session_uuid = ?;", (session_uuid,))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Scan session not found.")
            
            session_id = row["id"]
            current_status = row["status"]
            
            if current_status != "Paused":
                return False
                
            cursor.execute("UPDATE scan_sessions SET status = 'Running', updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (session_id,))
            cursor.execute("""
                UPDATE scan_session_tasks 
                SET status = 'Pending', updated_at = CURRENT_TIMESTAMP 
                WHERE session_id = ? AND status = 'Paused';
            """, (session_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def cancel_session(session_uuid: str) -> bool:
        """Cancels a session, aborting Pending and Paused tasks."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, status FROM scan_sessions WHERE session_uuid = ?;", (session_uuid,))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Scan session not found.")
            
            session_id = row["id"]
            
            cursor.execute("UPDATE scan_sessions SET status = 'Cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (session_id,))
            cursor.execute("""
                UPDATE scan_session_tasks 
                SET status = 'Cancelled', updated_at = CURRENT_TIMESTAMP 
                WHERE session_id = ? AND status IN ('Pending', 'Paused', 'Running');
            """, (session_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def retry_session(session_uuid: str) -> bool:
        """Re-enqueues failed or cancelled tasks inside a session."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, status FROM scan_sessions WHERE session_uuid = ?;", (session_uuid,))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Scan session not found.")
            
            session_id = row["id"]
            
            # Reset session state
            cursor.execute("UPDATE scan_sessions SET status = 'Pending', updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (session_id,))
            
            # Reset tasks in Failed or Cancelled state back to Pending
            cursor.execute("""
                UPDATE scan_session_tasks 
                SET status = 'Pending', error_message = NULL, updated_at = CURRENT_TIMESTAMP 
                WHERE session_id = ? AND status IN ('Failed', 'Cancelled');
            """, (session_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def get_session_progress(session_uuid: str) -> dict:
        """Calculates progress percent and updates session status based on sub-task states."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, case_id, status, progress_percent, created_at, updated_at FROM scan_sessions WHERE session_uuid = ?;", (session_uuid,))
            sess_row = cursor.fetchone()
            if not sess_row:
                raise ValueError("Scan session not found.")
            
            session_id = sess_row["id"]
            
            # Query all tasks for session
            cursor.execute("SELECT id, task_uuid, task_type, status, error_message FROM scan_session_tasks WHERE session_id = ?;", (session_id,))
            tasks = [dict(t) for t in cursor.fetchall()]
            
            total_tasks = len(tasks)
            completed_tasks = sum(1 for t in tasks if t["status"] == "Completed")
            failed_tasks = sum(1 for t in tasks if t["status"] == "Failed")
            cancelled_tasks = sum(1 for t in tasks if t["status"] == "Cancelled")
            
            # Progress calculation
            new_progress = 0.0
            if total_tasks > 0:
                new_progress = round((completed_tasks / total_tasks) * 100.0, 2)
            
            # Status resolution
            new_status = sess_row["status"]
            if sess_row["status"] in ("Pending", "Running"):
                if failed_tasks > 0:
                    new_status = "Failed"
                elif cancelled_tasks > 0:
                    new_status = "Cancelled"
                elif completed_tasks == total_tasks:
                    new_status = "Completed"
                elif completed_tasks > 0:
                    new_status = "Running"
            
            if new_status != sess_row["status"] or abs(new_progress - sess_row["progress_percent"]) > 0.01:
                cursor.execute("""
                    UPDATE scan_sessions 
                    SET status = ?, progress_percent = ?, updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?;
                """, (new_status, new_progress, session_id))
                conn.commit()
                
            return {
                "session_uuid": session_uuid,
                "case_id": sess_row["case_id"],
                "status": new_status,
                "progress_percent": new_progress,
                "created_at": sess_row["created_at"],
                "updated_at": sess_row["updated_at"],
                "tasks": tasks
            }
        finally:
            conn.close()

    @staticmethod
    def get_session_timeline(session_uuid: str) -> list:
        """Aggregates all events compiled during the session task sequence."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM scan_sessions WHERE session_uuid = ?;", (session_uuid,))
            sess_row = cursor.fetchone()
            if not sess_row:
                raise ValueError("Scan session not found.")
            
            session_id = sess_row["id"]
            
            # Fetch events linked to tasks
            cursor.execute("""
                SELECT t.task_type, t.status as task_status, t.updated_at, t.error_message
                FROM scan_session_tasks t
                WHERE t.session_id = ?
                ORDER BY t.created_at ASC, t.id ASC;
            """, (session_id,))
            rows = cursor.fetchall()
            
            timeline = []
            for r in rows:
                desc = f"Stage '{r['task_type']}' finished with status '{r['task_status']}'."
                if r["error_message"]:
                    desc += f" Error details: {r['error_message']}"
                timeline.append({
                    "timestamp_str": r["updated_at"],
                    "event_type": f"task_{r['task_type']}",
                    "description": desc
                })
            return timeline
        finally:
            conn.close()

    @staticmethod
    def recover_stuck_sessions():
        """Resets running sessions and tasks back to Pending on worker restart."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE scan_sessions SET status = 'Pending', updated_at = CURRENT_TIMESTAMP WHERE status = 'Running';")
            cursor.execute("UPDATE scan_session_tasks SET status = 'Pending', error_message = 'System restarted while task was processing.' WHERE status = 'Running';")
            conn.commit()
            logger.info("Auto-recovered stuck running scan sessions and tasks on startup.")
        except Exception as e:
            logger.error(f"Error during stuck sessions recovery: {e}")
        finally:
            conn.close()
