import time
import os
import json
import logging
from backend.services.ai_interfaces import IDetectionService, DependencyContainer
from backend.ai.services.orchestrator import AIServiceOrchestrator
from backend.database import get_db_connection
from backend.services.logger import log_scan_job
from backend.config import Config
from backend.services.cache import DetectionCache
from backend.services.model_manager import ModelLifecycleManager
from backend.services.metrics import AIMetricsCollector, log_ai_inference

logger = logging.getLogger("tsn.detection_service")

def compute_file_sha256(filepath: str) -> str:
    import hashlib
    try:
        h = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()
    except FileNotFoundError:
        return hashlib.sha256(filepath.encode('utf-8', errors='ignore')).hexdigest()

class DetectionService(IDetectionService):
    def __init__(self, cache_service=None, model_manager=None):
        container = DependencyContainer.get_instance()
        
        # Initialize defaults in container if not present
        try:
            container.resolve(DetectionCache)
        except KeyError:
            container.register(DetectionCache, DetectionCache())
            
        try:
            container.resolve(ModelLifecycleManager)
        except KeyError:
            container.register(ModelLifecycleManager, ModelLifecycleManager.get_instance())
            
        self.cache = cache_service or container.resolve(DetectionCache)
        self.model_manager = model_manager or container.resolve(ModelLifecycleManager)

    def run_detection_check(self, case_id: int, evidence_id: int, asset_file: str) -> dict:
        """Executes full detection check pipeline on an asset file against originals.
        
        Returns:
            dict: Structured comparison result payload corresponding to DetectionResult model.
        """
        if not asset_file or not os.path.exists(asset_file):
            raise FileNotFoundError(f"Asset file not found for detection processing: {asset_file}")
            
        start_time = time.time()
        
        # 1. Check cache if enabled
        cache_enabled = getattr(Config, "DETECTION_CACHE_ENABLED", True)
        asset_hash = compute_file_sha256(asset_file)
        cache_key = f"detection:{case_id}:{asset_hash}"
        
        metrics = AIMetricsCollector.get_instance()

        if cache_enabled:
            cached_res = self.cache.get(cache_key)
            if cached_res:
                metrics.record_cache_event(hit=True)
                res = json.loads(cached_res)
                processing_time = time.time() - start_time
                log_scan_job("DETECTION_JOB", evidence_id, "Completed", f"model=MultiModalScore score={res['overall_similarity']:.4f} processing_time={processing_time:.2f}s status=Completed (Cache Hit)")
                return res
            else:
                metrics.record_cache_event(hit=False)

        max_similarity_score = 0.0
        best_confidence_score = 0.0
        best_confidence_level = "Low"
        best_explanation = "No comparison matching run executed."
        best_modality_scores = {
            "visual": 0.0,
            "acoustic": 0.0,
            "ocr": 0.0,
            "logo": 0.0,
            "metadata": 0.0
        }
        best_agreements = []

        # Fast-path SHA-256 duplicate check
        fast_path_matched = False
        try:
            conn_meta = get_db_connection()
            cursor_meta = conn_meta.cursor()
            cursor_meta.execute("SELECT id, filesize, file_uuid FROM originals WHERE case_id = ?;", (case_id,))
            originals_meta = cursor_meta.fetchall()
            conn_meta.close()

            asset_size = os.path.getsize(asset_file)
            for orig in originals_meta:
                orig_id = orig["id"]
                orig_size = orig["filesize"]
                orig_uuid = orig["file_uuid"]
                
                # Compare file sizes as pre-filter
                if asset_size == orig_size:
                    original_dir = os.path.join(Config.PROJECT_ROOT, Config.STORAGE_DIR, "originals")
                    original_filepath = None
                    if os.path.exists(original_dir):
                        for fn in os.listdir(original_dir):
                            if fn.startswith(orig_uuid):
                                original_filepath = os.path.join(original_dir, fn)
                                break
                                
                    if original_filepath and os.path.exists(original_filepath):
                        orig_hash = compute_file_sha256(original_filepath)
                        if asset_hash == orig_hash:
                            max_similarity_score = 1.0
                            best_confidence_score = 1.0
                            best_confidence_level = "High"
                            best_explanation = "Exact duplicate detected via fast-path SHA-256 hash validation."
                            best_modality_scores = {
                                "visual": 1.0,
                                "acoustic": 1.0,
                                "ocr": 1.0,
                                "logo": 1.0,
                                "metadata": 1.0
                            }
                            best_agreements = ["exact_checksum_match"]
                            fast_path_matched = True
                            break
        except Exception as fast_path_err:
            logger.warning(f"Fast-path duplicate check bypassed: {fast_path_err}")

        max_retries = getattr(Config, "AI_MODEL_RETRY_COUNT", 3)
        backoff_factor = getattr(Config, "AI_MODEL_RETRY_BACKOFF", 2.0)
        
        attempt = 0
        success = False
        last_err = None

        if fast_path_matched:
            success = True
        else:
            while attempt <= max_retries:
                try:
                    # Preload models via model lifecycle manager
                    self.model_manager.load_model("clip")
                    self.model_manager.load_model("sentence_transformers")
                    self.model_manager.load_model("whisper")

                    # Ingest fingerprint via orchestrator
                    evidence_fp_id = AIServiceOrchestrator.ingest_fingerprint(case_id, "evidence", evidence_id, asset_file)
                    
                    # Get originals of the case
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("SELECT id FROM originals WHERE case_id = ?;", (case_id,))
                    originals = cursor.fetchall()
                    conn.close()

                    # Check similarity against each original reference asset
                    for orig in originals:
                        orig_id = orig[0] if isinstance(orig, (tuple, list)) else orig["id"]
                        
                        sim_res = AIServiceOrchestrator.check_similarity(
                            case_id=case_id,
                            source_id=evidence_id,
                            source_type="evidence",
                            target_id=orig_id,
                            target_type="original",
                            match_types=["perceptual_hash", "embedding"]
                        )
                        
                        score = sim_res.get("overall_score", 0.0)
                        if score > max_similarity_score:
                            max_similarity_score = score
                            
                            conn_fp = get_db_connection()
                            cursor_fp = conn_fp.cursor()
                            cursor_fp.execute("SELECT fingerprint_json FROM originals WHERE id = ?;", (orig_id,))
                            orig_row = cursor_fp.fetchone()
                            
                            cursor_fp.execute("SELECT phash, ahash, dhash, metadata_hash, ocr_fingerprint FROM fingerprints WHERE entity_type = 'evidence' AND entity_id = ? ORDER BY id DESC LIMIT 1;", (evidence_id,))
                            ev_fp_row = cursor_fp.fetchone()
                            conn_fp.close()
                            
                            if orig_row and orig_row[0] and ev_fp_row:
                                try:
                                    orig_fp = json.loads(orig_row[0])
                                    ev_fp = {
                                        "fingerprint": [{"hash": ev_fp_row[2], "offset": 0.0}], # dhash
                                        "audio_peaks": [],
                                        "logo_metadata": [],
                                        "ocr_text": ev_fp_row[4] or ""
                                    }
                                    
                                    from backend.fingerprint import compare_fingerprints
                                    conf, report = compare_fingerprints(orig_fp, ev_fp)
                                    best_confidence_score = report.get("confidence_score", 0.0)
                                    best_confidence_level = report.get("confidence_level", "Low")
                                    best_explanation = report.get("explanation", "")
                                    best_modality_scores = report.get("weighted_evidence", best_modality_scores)
                                    best_agreements = report.get("agreements", [])
                                except Exception:
                                    pass
                    success = True
                    break
                except Exception as e:
                    last_err = e
                    attempt += 1
                    if attempt <= max_retries:
                        sleep_time = backoff_factor ** attempt
                        logger.warning(f"Transient AI failure: {e}. Retrying in {sleep_time}s (Attempt {attempt}/{max_retries})...")
                        time.sleep(sleep_time)
                    else:
                        logger.error(f"AI failure retries exhausted: {e}")

        processing_time = time.time() - start_time
        
        if not success:
            metrics.record_inference("MultiModalScore", success=False, latency_ms=processing_time * 1000)
            log_ai_inference("MultiModalScore", "DetectionCheck", "Failed", f"case_id={case_id} evidence_id={evidence_id}", processing_time * 1000, str(last_err))
            raise last_err if last_err else RuntimeError("Unknown error during detection check execution.")

        # Record metrics & log success
        metrics.record_inference("MultiModalScore", success=True, latency_ms=processing_time * 1000)
        log_ai_inference("MultiModalScore", "DetectionCheck", "Success", f"case_id={case_id} score={max_similarity_score:.4f}", processing_time * 1000)

        log_scan_job("DETECTION_JOB", evidence_id, "Completed", f"model=MultiModalScore score={max_similarity_score:.4f} processing_time={processing_time:.2f}s status=Completed")
        
        result_payload = {
            "evidence_id": evidence_id,
            "case_id": case_id,
            "overall_similarity": round(max_similarity_score, 4),
            "confidence_score": round(best_confidence_score, 4),
            "confidence_level": best_confidence_level,
            "explanation": best_explanation,
            "modality_scores": best_modality_scores,
            "agreements": best_agreements
        }

        # Cache result
        if cache_enabled:
            self.cache.set(cache_key, json.dumps(result_payload))
            
        return result_payload

