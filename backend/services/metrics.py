import os
import sys
import json
import time
import logging
from datetime import datetime
from backend.config import Config

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LOG_DIR = os.path.join(PROJECT_ROOT, getattr(Config, "STORAGE_DIR", "storage"), "logs")
os.makedirs(LOG_DIR, exist_ok=True)

AI_LOG_FILE = os.path.join(LOG_DIR, "ai_execution.log")
logger = logging.getLogger("tsn.metrics")

class AIMetricsCollector:
    _instance = None

    def __init__(self):
        self.metrics = {
            "inferences_total": 0,
            "inferences_success": 0,
            "inferences_failed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "latencies_ms": {},
        }
        import threading
        self.lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def record_inference(self, model_name: str, success: bool, latency_ms: float):
        with self.lock:
            self.metrics["inferences_total"] += 1
            if success:
                self.metrics["inferences_success"] += 1
            else:
                self.metrics["inferences_failed"] += 1
            
            if model_name not in self.metrics["latencies_ms"]:
                self.metrics["latencies_ms"][model_name] = []
            
            self.metrics["latencies_ms"][model_name].append(latency_ms)
            if len(self.metrics["latencies_ms"][model_name]) > 1000:
                self.metrics["latencies_ms"][model_name].pop(0)

    def record_cache_event(self, hit: bool):
        with self.lock:
            if hit:
                self.metrics["cache_hits"] += 1
            else:
                self.metrics["cache_misses"] += 1

    def get_metrics(self) -> dict:
        with self.lock:
            summary = {
                "inferences_total": self.metrics["inferences_total"],
                "inferences_success": self.metrics["inferences_success"],
                "inferences_failed": self.metrics["inferences_failed"],
                "cache_hits": self.metrics["cache_hits"],
                "cache_misses": self.metrics["cache_misses"],
                "model_stats": {}
            }
            
            for model, latencies in self.metrics["latencies_ms"].items():
                if latencies:
                    summary["model_stats"][model] = {
                        "avg_latency_ms": round(sum(latencies) / len(latencies), 2),
                        "max_latency_ms": round(max(latencies), 2),
                        "min_latency_ms": round(min(latencies), 2),
                        "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 2) if len(latencies) >= 20 else round(max(latencies), 2),
                        "count": len(latencies)
                    }
                else:
                    summary["model_stats"][model] = {
                        "avg_latency_ms": 0.0,
                        "max_latency_ms": 0.0,
                        "min_latency_ms": 0.0,
                        "p95_latency_ms": 0.0,
                        "count": 0
                    }
            return summary


def log_ai_inference(model_name: str, action: str, status: str, input_details: str = "", elapsed_ms: float = 0.0, error: str = None):
    """Logs structured JSON AI execution entry to ai_execution.log."""
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "model_name": model_name,
        "action": action,
        "status": status,
        "input_details": input_details,
        "elapsed_ms": round(elapsed_ms, 2),
        "error": error
    }
    
    try:
        with open(AI_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to write structured AI log: {e}. Entry was: {log_entry}")
