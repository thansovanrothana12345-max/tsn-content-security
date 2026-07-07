import logging
import logging.handlers
import os
from backend.config import Config

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(PROJECT_ROOT, Config.STORAGE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

log_file = os.path.join(LOG_DIR, "app.log")
log_handler = logging.handlers.RotatingFileHandler(
    log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
)
formatter = logging.Formatter("[%(asctime)s] %(levelname)s [%(name)s] %(message)s")
log_handler.setFormatter(formatter)

logger = logging.getLogger("tsn")
logger.setLevel(logging.INFO)

# Avoid duplicate handlers in multiple imports
if not logger.handlers:
    logger.addHandler(log_handler)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

def log_scan_job(action: str, job_id: int, status: str, details: str = ""):
    logger.info(f"[SCAN_JOB] [ACTION={action}] [JOB_ID={job_id}] [STATUS={status}] {details}")

def log_evidence(action: str, evidence_id: int, status: str, details: str = ""):
    logger.info(f"[EVIDENCE] [ACTION={action}] [EVIDENCE_ID={evidence_id}] [STATUS={status}] {details}")

def log_worker(action: str, details: str = "", status: str = "INFO"):
    log_msg = f"[BACKGROUND_WORKER] [ACTION={action}] {details}"
    if status == "ERROR":
        logger.error(log_msg)
    elif status == "WARNING":
        logger.warning(log_msg)
    else:
        logger.info(log_msg)

def log_connector(platform: str, action: str, details: str = "", status: str = "INFO"):
    log_msg = f"[CONNECTOR] [PLATFORM={platform}] [ACTION={action}] {details}"
    if status == "ERROR":
        logger.error(log_msg)
    else:
        logger.info(log_msg)

def log_api_error(path: str, error_msg: str, status_code: int = 500):
    logger.error(f"[API_ERROR] [PATH={path}] [STATUS_CODE={status_code}] {error_msg}")
