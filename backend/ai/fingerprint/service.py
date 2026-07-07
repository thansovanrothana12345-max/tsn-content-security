from PIL import Image
import os
import hashlib
from backend.ai.hashing.service import HashingService
from backend.ai.embeddings.service import EmbeddingsService
from backend.ai.detectors.service import DetectorsService
from backend.services.ai_interfaces import ImageFingerprintInterface, VideoFingerprintInterface, AudioFingerprintInterface

class FingerprintService(ImageFingerprintInterface, VideoFingerprintInterface, AudioFingerprintInterface):
    @classmethod
    def fingerprint_image(cls, pil_img: Image.Image) -> dict:
        """Computes perceptual hashes, embeddings, and ORB keypoints for an image."""
        # 1. Hashing
        phash = HashingService.calculate_phash(pil_img)
        ahash = HashingService.calculate_ahash(pil_img)
        dhash = HashingService.calculate_dhash(pil_img)
        
        # 2. Embeddings
        embedding = EmbeddingsService.generate_image_embedding(pil_img)
        
        # 3. Detectors (ORB)
        kp_json, desc_binary = DetectorsService.extract_orb_features(pil_img)
        
        return {
            "phash": phash,
            "ahash": ahash,
            "dhash": dhash,
            "embedding": embedding,
            "keypoints_json": kp_json,
            "descriptors_binary": desc_binary
        }

    @classmethod
    def fingerprint_video(cls, video_path: str, interval_sec: float = 1.0) -> list[dict]:
        """Processes video frames at intervals and generates visual sequence fingerprints."""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
        # Get frame hashes and timestamps
        frames = HashingService.calculate_video_hashes(video_path, interval_sec)
        
        # Import CV2 inside method to avoid dependency locks
        import cv2
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return []
            
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0:
            fps = 25.0
            
        frame_interval = int(fps * interval_sec)
        frame_idx = 0
        results = []
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_idx % frame_interval == 0:
                timestamp = float(frame_idx) / fps
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_frame)
                
                # Retrieve hashes from precomputed frames list
                matched_hashes = [f for f in frames if f["frame_index"] == frame_idx]
                if matched_hashes:
                    fh = matched_hashes[0]
                else:
                    fh = {
                        "phash": HashingService.calculate_phash(pil_img),
                        "ahash": HashingService.calculate_ahash(pil_img),
                        "dhash": HashingService.calculate_dhash(pil_img)
                    }
                    
                # Generate embeddings & ORB features
                embedding = EmbeddingsService.generate_image_embedding(pil_img)
                kp_json, desc_binary = DetectorsService.extract_orb_features(pil_img)
                
                results.append({
                    "frame_index": frame_idx,
                    "timestamp_sec": timestamp,
                    "phash": fh["phash"],
                    "ahash": fh["ahash"],
                    "dhash": fh["dhash"],
                    "embedding": embedding,
                    "keypoints_json": kp_json,
                    "descriptors_binary": desc_binary
                })
                
            frame_idx += 1
            
        cap.release()
        return results

    @classmethod
    def fingerprint_audio(cls, audio_path: str) -> dict:
        """Computes audio segment embeddings and md5 metadata hashes."""
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
            
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
            
        md5_hash = hashlib.md5(audio_bytes).hexdigest()
        audio_emb = EmbeddingsService.generate_audio_embedding(audio_bytes)
        
        return {
            "metadata_hash": md5_hash,
            "embedding": audio_emb
        }
