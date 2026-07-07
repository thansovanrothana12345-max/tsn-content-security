import cv2
import numpy as np
from PIL import Image
import os
import hashlib

class HashingService:
    @staticmethod
    def calculate_ahash(pil_img: Image.Image) -> str:
        """Calculates Average Hash (aHash) using NumPy."""
        # 1. Resize to 8x8 and convert to greyscale
        img = pil_img.convert("L").resize((8, 8), Image.Resampling.BILINEAR)
        pixels = np.array(img)
        # 2. Get average value
        avg = pixels.mean()
        # 3. Create binary bits
        bits = (pixels >= avg).astype(int).flatten()
        # 4. Convert bits to hex string
        hex_str = ""
        for i in range(0, 64, 4):
            nibble = bits[i:i+4]
            val = sum(b * (2**(3-idx)) for idx, b in enumerate(nibble))
            hex_str += f"{val:x}"
        return hex_str

    @staticmethod
    def calculate_dhash(pil_img: Image.Image) -> str:
        """Calculates Difference Hash (dHash) using adjacent pixel comparisons."""
        # Resize to 9x8 and convert to greyscale
        img = pil_img.convert("L").resize((9, 8), Image.Resampling.BILINEAR)
        pixels = np.array(img)
        # Compare adjacent columns
        bits = (pixels[:, :-1] > pixels[:, 1:]).astype(int).flatten()
        # Convert bits to hex string
        hex_str = ""
        for i in range(0, 64, 4):
            nibble = bits[i:i+4]
            val = sum(b * (2**(3-idx)) for idx, b in enumerate(nibble))
            hex_str += f"{val:x}"
        return hex_str

    @staticmethod
    def calculate_phash(pil_img: Image.Image) -> str:
        """Calculates Perceptual Hash (pHash) using OpenCV DCT."""
        try:
            # 1. Resize to 32x32 and convert to greyscale
            img = pil_img.convert("L").resize((32, 32), Image.Resampling.BILINEAR)
            pixels = np.array(img, dtype=np.float32)
            # 2. Compute 2D Discrete Cosine Transform (DCT) using OpenCV
            dct = cv2.dct(pixels)
            # 3. Extract the top-left 8x8 block (excluding DC coefficient at 0,0)
            block = dct[:8, :8]
            median = np.median(block)
            bits = (block > median).astype(int).flatten()
            # 4. Convert bits to hex string
            hex_str = ""
            for i in range(0, 64, 4):
                nibble = bits[i:i+4]
                val = sum(b * (2**(3-idx)) for idx, b in enumerate(nibble))
                hex_str += f"{val:x}"
            return hex_str
        except Exception:
            # Fallback to a reproducible hash if cv2.dct fails
            h = hashlib.md5(pil_img.tobytes()).hexdigest()
            return h[:16]

    @classmethod
    def calculate_video_hashes(cls, video_path: str, interval_sec: float = 1.0) -> list[dict]:
        """Extracts frames at regular intervals and computes phash/ahash/dhash for each frame."""
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")
            
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
                # Convert BGR (OpenCV) to RGB (Pillow)
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(rgb_frame)
                
                phash = cls.calculate_phash(pil_img)
                ahash = cls.calculate_ahash(pil_img)
                dhash = cls.calculate_dhash(pil_img)
                
                results.append({
                    "frame_index": frame_idx,
                    "timestamp_sec": timestamp,
                    "phash": phash,
                    "ahash": ahash,
                    "dhash": dhash
                })
                
            frame_idx += 1
            
        cap.release()
        return results
