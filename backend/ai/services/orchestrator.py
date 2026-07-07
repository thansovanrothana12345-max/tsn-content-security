import os
import json
import sqlite3
import numpy as np
from PIL import Image
from backend.database import get_db_connection
from backend.ai.fingerprint.service import FingerprintService
from backend.ai.similarity.service import SimilarityService

class AIServiceOrchestrator:
    @classmethod
    def ingest_fingerprint(cls, case_id: int, entity_type: str, entity_id: int, file_path: str) -> int:
        """Processes any media file, generates its AI fingerprints, and stores them in the DB.
        
        Returns:
            int: The generated fingerprint record ID.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Source file not found: {file_path}")
            
        ext = os.path.splitext(file_path)[1].lower()
        
        # 1. Generate appropriate fingerprint
        phash = None
        ahash = None
        dhash = None
        whash = None
        metadata_hash = None
        ocr_fingerprint = None
        
        image_emb = None
        video_embs = [] # list of dicts
        audio_emb = None
        
        kp_json = "[]"
        desc_binary = b""
        
        # Check type
        if ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
            # Image
            with Image.open(file_path) as img:
                fp = FingerprintService.fingerprint_image(img)
                phash = fp["phash"]
                ahash = fp["ahash"]
                dhash = fp["dhash"]
                image_emb = fp["embedding"]
                kp_json = fp["keypoints_json"]
                desc_binary = fp["descriptors_binary"]
                
        elif ext in [".mp4", ".avi", ".mov", ".mkv"]:
            # Video
            frames_fp = FingerprintService.fingerprint_video(file_path)
            if frames_fp:
                # Use the middle frame's perceptual hash as the representative hash
                mid_idx = len(frames_fp) // 2
                phash = frames_fp[mid_idx]["phash"]
                ahash = frames_fp[mid_idx]["ahash"]
                dhash = frames_fp[mid_idx]["dhash"]
                video_embs = frames_fp
                
        elif ext in [".mp3", ".wav", ".aac", ".flac", ".m4a"]:
            # Audio
            fp = FingerprintService.fingerprint_audio(file_path)
            metadata_hash = fp["metadata_hash"]
            audio_emb = fp["embedding"]
            
        else:
            # Fallback metadata hash
            import hashlib
            with open(file_path, "rb") as f:
                metadata_hash = hashlib.md5(f.read()).hexdigest()
                
        # 2. Insert into DB
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT INTO fingerprints (case_id, entity_type, entity_id, phash, ahash, dhash, whash, metadata_hash, ocr_fingerprint)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (case_id, entity_type, entity_id, phash, ahash, dhash, whash, metadata_hash, ocr_fingerprint))
            
            fingerprint_id = cursor.lastrowid
            
            # Save Image Embedding
            if image_emb is not None:
                cursor.execute("""
                    INSERT INTO image_embeddings (fingerprint_id, model_name, embedding, dimensions)
                    VALUES (?, 'CLIP-512', ?, ?)
                """, (fingerprint_id, image_emb.tobytes(), len(image_emb)))
                
            # Save Video Embeddings sequence
            for frame in video_embs:
                cursor.execute("""
                    INSERT INTO video_embeddings (fingerprint_id, model_name, frame_index, timestamp_sec, embedding, dimensions)
                    VALUES (?, 'CLIP-512-Frame', ?, ?, ?, ?)
                """, (fingerprint_id, frame["frame_index"], frame["timestamp_sec"], frame["embedding"].tobytes(), len(frame["embedding"])))
                
            # Save Audio Embedding
            if audio_emb is not None:
                cursor.execute("""
                    INSERT INTO audio_embeddings (fingerprint_id, model_name, timestamp_start, timestamp_end, embedding, dimensions)
                    VALUES (?, 'Whisper-Placeholder', 0.0, 0.0, ?, ?)
                """, (fingerprint_id, audio_emb.tobytes(), len(audio_emb)))
                
            # Save Feature Vector descriptors
            if desc_binary:
                cursor.execute("""
                    INSERT INTO feature_vectors (fingerprint_id, feature_type, keypoints_json, descriptors_binary)
                    VALUES (?, 'ORB', ?, ?)
                """, (fingerprint_id, kp_json, desc_binary))
                
            conn.commit()
            return fingerprint_id
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    @classmethod
    def check_similarity(cls, case_id: int, source_id: int, source_type: str, target_id: int, target_type: str, match_types: list[str] = None) -> dict:
        """Queries and compares fingerprints between two entities."""
        if not match_types:
            match_types = ["perceptual_hash", "embedding"]
            
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # 1. Fetch source fingerprint
            cursor.execute("""
                SELECT id, phash, ahash, dhash, metadata_hash, ocr_fingerprint
                FROM fingerprints
                WHERE case_id = ? AND entity_type = ? AND entity_id = ?
                ORDER BY id DESC LIMIT 1
            """, (case_id, source_type, source_id))
            src_row = cursor.fetchone()
            
            # 2. Fetch target fingerprint
            cursor.execute("""
                SELECT id, phash, ahash, dhash, metadata_hash, ocr_fingerprint
                FROM fingerprints
                WHERE case_id = ? AND entity_type = ? AND entity_id = ?
                ORDER BY id DESC LIMIT 1
            """, (case_id, target_type, target_id))
            tgt_row = cursor.fetchone()
            
            if not src_row or not tgt_row:
                return {
                    "overall_score": 0.0,
                    "matches": {},
                    "decision": "No Match",
                    "error": "Fingerprints not found for one or both target entities. Run scan/fingerprinting first."
                }
                
            src_fp_id = src_row["id"]
            tgt_fp_id = tgt_row["id"]
            
            scores = {}
            
            # Match 1: Perceptual Hash
            if "perceptual_hash" in match_types:
                if src_row["phash"] and tgt_row["phash"]:
                    scores["perceptual_hash"] = SimilarityService.normalized_hamming_similarity(src_row["phash"], tgt_row["phash"])
                else:
                    scores["perceptual_hash"] = 0.0
                    
            # Match 2: Deep Vector Embeddings
            if "embedding" in match_types:
                # Check image embeddings
                cursor.execute("SELECT embedding FROM image_embeddings WHERE fingerprint_id = ?", (src_fp_id,))
                src_emb_row = cursor.fetchone()
                cursor.execute("SELECT embedding FROM image_embeddings WHERE fingerprint_id = ?", (tgt_fp_id,))
                tgt_emb_row = cursor.fetchone()
                
                if src_emb_row and tgt_emb_row:
                    src_emb = np.frombuffer(src_emb_row["embedding"], dtype=np.float32)
                    tgt_emb = np.frombuffer(tgt_emb_row["embedding"], dtype=np.float32)
                    scores["embedding"] = SimilarityService.cosine_similarity(src_emb, tgt_emb)
                else:
                    scores["embedding"] = 0.0
                    
            # Calculate overall score
            if scores:
                overall_score = sum(scores.values()) / len(scores)
            else:
                overall_score = 0.0
                
            # Compute final decision text
            if overall_score >= 0.85:
                decision = "Verified Copy"
            elif overall_score >= 0.50:
                decision = "Partial Copy / Substantial Reuse"
            else:
                decision = "No Match"
                
            return {
                "overall_score": round(overall_score, 4),
                "matches": {k: round(v, 4) for k, v in scores.items()},
                "decision": decision
            }
        finally:
            conn.close()
