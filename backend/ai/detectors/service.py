import cv2
import numpy as np
from PIL import Image
import json

class DetectorsService:
    @staticmethod
    def extract_orb_features(pil_img: Image.Image) -> tuple[str, bytes]:
        """Detects keypoints and computes ORB descriptors using OpenCV.
        
        Returns:
            tuple: (keypoints_json: str, descriptors_binary: bytes)
        """
        try:
            # 1. Convert PIL image to OpenCV format (BGR then Grayscale)
            cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
            gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
            
            # 2. Instantiate ORB Detector
            orb = cv2.ORB_create(nfeatures=500)
            
            # 3. Detect keypoints and compute descriptors
            keypoints, descriptors = orb.detectAndCompute(gray, None)
            
            if keypoints is None or descriptors is None:
                return "[]", b""
                
            # 4. Serialize keypoints to a compact JSON list of dicts
            kp_list = []
            for kp in keypoints:
                kp_list.append({
                    "pt": kp.pt,
                    "size": kp.size,
                    "angle": kp.angle,
                    "response": kp.response,
                    "octave": kp.octave,
                    "class_id": kp.class_id
                })
            
            kp_json = json.dumps(kp_list)
            # Serialize descriptors array to binary bytes
            desc_binary = descriptors.tobytes()
            
            return kp_json, desc_binary
        except Exception:
            # Return empty fallbacks if OpenCV processing fails
            return "[]", b""
            
    @staticmethod
    def deserialize_descriptors(desc_bytes: bytes) -> np.ndarray:
        """Deserializes ORB descriptors from raw binary back to a NumPy array."""
        if not desc_bytes:
            return None
        # ORB descriptors are uint8 arrays of shape (N, 32)
        arr = np.frombuffer(desc_bytes, dtype=np.uint8)
        # Reshape to (N, 32)
        n_features = len(arr) // 32
        if n_features == 0:
            return None
        return arr.reshape((n_features, 32))
