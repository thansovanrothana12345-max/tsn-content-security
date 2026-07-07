import time
import os
import json
from backend.services.ai_interfaces import IDetectionService
from backend.ai.services.orchestrator import AIServiceOrchestrator
from backend.database import get_db_connection
from backend.services.logger import log_scan_job
from backend.config import Config

class DetectionService(IDetectionService):
    def run_detection_check(self, case_id: int, evidence_id: int, asset_file: str) -> dict:
        """Executes full detection check pipeline on an asset file against originals.
        
        Returns:
            dict: Structured comparison result payload corresponding to DetectionResult model.
        """
        if not asset_file or not os.path.exists(asset_file):
            raise FileNotFoundError(f"Asset file not found for detection processing: {asset_file}")
            
        start_time = time.time()
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

        # 1. Ingest fingerprint via orchestrator
        evidence_fp_id = AIServiceOrchestrator.ingest_fingerprint(case_id, "evidence", evidence_id, asset_file)
        
        # 2. Get originals of the case
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM originals WHERE case_id = ?;", (case_id,))
        originals = cursor.fetchall()
        conn.close()

        # 3. Check similarity against each original reference asset
        for orig in originals:
            orig_id = orig[0] if isinstance(orig, (tuple, list)) else orig["id"]
            
            # AIServiceOrchestrator.check_similarity executes similarity comparisons
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
                
                # Fetch detailed report statistics from fingerprint comparison
                # We can call compare_fingerprints directly or use check_similarity returns
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
                        # Build minimal fp for comparison
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
                        
        processing_time = time.time() - start_time
        log_scan_job("DETECTION_JOB", evidence_id, "Completed", f"model=MultiModalScore score={max_similarity_score:.4f} processing_time={processing_time:.2f}s status=Completed")
        
        return {
            "evidence_id": evidence_id,
            "case_id": case_id,
            "overall_similarity": round(max_similarity_score, 4),
            "confidence_score": round(best_confidence_score, 4),
            "confidence_level": best_confidence_level,
            "explanation": best_explanation,
            "modality_scores": best_modality_scores,
            "agreements": best_agreements
        }
