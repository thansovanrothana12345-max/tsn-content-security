import numpy as np
from PIL import Image
import hashlib
from backend.ai.models.loader import ModelLoader

class EmbeddingsService:
    IMAGE_DIM = 512
    TEXT_DIM = 768

    @classmethod
    def generate_image_embedding(cls, pil_img: Image.Image) -> np.ndarray:
        """Generates a 512-dimension vector embedding for an image."""
        model = ModelLoader.get_clip_model()
        if model:
            # Placeholder for CLIP implementation when installed
            # import torch, clip
            # return clip_vector
            pass
            
        # Fallback: Deterministic vector generated from image content
        # Resize to 16x16 (256 pixels) in RGB, flatten, and pad/manipulate to get 512 dims
        img_resized = pil_img.convert("RGB").resize((16, 16), Image.Resampling.BILINEAR)
        pixels = np.array(img_resized, dtype=np.float32) / 255.0
        flat = pixels.flatten()  # 16 * 16 * 3 = 768 dimensions
        
        # Take the first 512 dimensions
        vector = flat[:cls.IMAGE_DIM]
        if len(vector) < cls.IMAGE_DIM:
            # Pad if necessary
            vector = np.pad(vector, (0, cls.IMAGE_DIM - len(vector)), 'constant')
            
        # Normalize to unit length (L2 norm)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        return vector

    @classmethod
    def generate_text_embedding(cls, text: str) -> np.ndarray:
        """Generates a 768-dimension vector embedding for text / OCR content."""
        model = ModelLoader.get_sentence_transformer()
        if model:
            # Placeholder for SentenceTransformers implementation when installed
            # return model.encode([text])[0]
            pass
            
        # Fallback: Seeded random generation to make it deterministic for the input text
        hasher = hashlib.sha256(text.encode('utf-8', errors='ignore'))
        seed = int(hasher.hexdigest()[:8], 16)
        
        # Set random state seed locally to avoid interfering with global random states
        rng = np.random.default_rng(seed)
        vector = rng.standard_normal(cls.TEXT_DIM, dtype=np.float32)
        
        # Normalize to unit length
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
            
        return vector

    @classmethod
    def generate_audio_embedding(cls, audio_bytes: bytes) -> np.ndarray:
        """Generates a 128-dimension mock/placeholder vector embedding for audio segments."""
        hasher = hashlib.sha256(audio_bytes)
        seed = int(hasher.hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        vector = rng.standard_normal(128, dtype=np.float32)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector
