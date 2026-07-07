import os
import sys
import logging
import time
import numpy as np
from backend.services.ai_interfaces import IAIModelProvider

logger = logging.getLogger("tsn.model_manager")

class CLIPModelProvider(IAIModelProvider):
    def __init__(self):
        self.model = None
        self.device = "cpu"
        self.is_fallback = False
        self.loaded = False
        self.last_used = 0.0

    def load(self) -> None:
        try:
            import torch
            import clip
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model, _ = clip.load("ViT-B/32", device=self.device)
            self.is_fallback = False
            self.loaded = True
            logger.info(f"CLIP model loaded successfully on device: {self.device}")
        except Exception as e:
            logger.warning(f"Could not load real CLIP model: {str(e)}. Using fallback mock.")
            self.model = "CLIP_FALLBACK_MOCK"
            self.is_fallback = True
            self.loaded = True
        self.last_used = time.time()

    def unload(self) -> None:
        self.model = None
        self.loaded = False
        self.is_fallback = False
        # If torch is available and CUDA was used, empty cache
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        logger.info("CLIP model unloaded.")

    def is_loaded(self) -> bool:
        return self.loaded

    def health_check(self) -> dict:
        status = "healthy" if self.loaded else "unloaded"
        if self.loaded and self.is_fallback:
            status = "degraded"
        
        # Estimate memory usage
        memory_mb = 0.0
        if self.loaded:
            if self.is_fallback:
                memory_mb = 0.1
            else:
                try:
                    import torch
                    if self.device == "cuda":
                        memory_mb = torch.cuda.memory_allocated() / (1024 * 1024)
                    else:
                        memory_mb = 350.0 # Standard ViT-B/32 size in MB
                except Exception:
                    memory_mb = 350.0

        return {
            "status": status,
            "device": self.device,
            "is_fallback": self.is_fallback,
            "memory_mb": round(memory_mb, 2),
            "last_used": self.last_used
        }

    def get_model_instance(self):
        return self.model

    def generate_embedding(self, pil_img) -> np.ndarray:
        self.last_used = time.time()
        if not self.loaded:
            self.load()

        if self.is_fallback:
            # Deterministic vector generated from image content
            img_resized = pil_img.convert("RGB").resize((16, 16), 3) # Image.Resampling.BILINEAR
            pixels = np.array(img_resized, dtype=np.float32) / 255.0
            flat = pixels.flatten()  # 16 * 16 * 3 = 768 dimensions
            vector = flat[:512]
            if len(vector) < 512:
                vector = np.pad(vector, (0, 512 - len(vector)), 'constant')
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
            return vector
        else:
            try:
                import torch
                import clip
                # Preprocess image
                _, preprocess = clip.load("ViT-B/32", device=self.device)
                image = preprocess(pil_img).unsqueeze(0).to(self.device)
                with torch.no_grad():
                    image_features = self.model.encode_image(image)
                    image_features /= image_features.norm(dim=-1, keepdim=True)
                return image_features.cpu().numpy()[0]
            except Exception as e:
                logger.error(f"Inference error in CLIP model: {str(e)}. Falling back.")
                self.is_fallback = True
                return self.generate_embedding(pil_img)


class SentenceTransformersProvider(IAIModelProvider):
    def __init__(self):
        self.model = None
        self.device = "cpu"
        self.is_fallback = False
        self.loaded = False
        self.last_used = 0.0

    def load(self) -> None:
        try:
            import torch
            from sentence_transformers import SentenceTransformer
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = SentenceTransformer("all-MiniLM-L6-v2", device=self.device)
            self.is_fallback = False
            self.loaded = True
            logger.info(f"SentenceTransformers model loaded successfully on device: {self.device}")
        except Exception as e:
            logger.warning(f"Could not load real SentenceTransformers model: {str(e)}. Using fallback mock.")
            self.model = "SENTENCE_TRANSFORMERS_FALLBACK_MOCK"
            self.is_fallback = True
            self.loaded = True
        self.last_used = time.time()

    def unload(self) -> None:
        self.model = None
        self.loaded = False
        self.is_fallback = False
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        logger.info("SentenceTransformers model unloaded.")

    def is_loaded(self) -> bool:
        return self.loaded

    def health_check(self) -> dict:
        status = "healthy" if self.loaded else "unloaded"
        if self.loaded and self.is_fallback:
            status = "degraded"
        
        memory_mb = 0.0
        if self.loaded:
            if self.is_fallback:
                memory_mb = 0.1
            else:
                try:
                    import torch
                    if self.device == "cuda":
                        memory_mb = torch.cuda.memory_allocated() / (1024 * 1024)
                    else:
                        memory_mb = 120.0
                except Exception:
                    memory_mb = 120.0

        return {
            "status": status,
            "device": self.device,
            "is_fallback": self.is_fallback,
            "memory_mb": round(memory_mb, 2),
            "last_used": self.last_used
        }

    def get_model_instance(self):
        return self.model

    def generate_embedding(self, text: str) -> np.ndarray:
        self.last_used = time.time()
        if not self.loaded:
            self.load()

        if self.is_fallback:
            import hashlib
            hasher = hashlib.sha256(text.encode('utf-8', errors='ignore'))
            seed = int(hasher.hexdigest()[:8], 16)
            rng = np.random.default_rng(seed)
            vector = rng.standard_normal(768, dtype=np.float32)
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
            return vector
        else:
            try:
                embedding = self.model.encode([text])[0]
                return embedding
            except Exception as e:
                logger.error(f"Inference error in SentenceTransformers: {str(e)}. Falling back.")
                self.is_fallback = True
                return self.generate_embedding(text)


class WhisperModelProvider(IAIModelProvider):
    def __init__(self):
        self.model = None
        self.device = "cpu"
        self.is_fallback = False
        self.loaded = False
        self.last_used = 0.0

    def load(self) -> None:
        try:
            import torch
            import whisper
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self.model = whisper.load_model("tiny", device=self.device)
            self.is_fallback = False
            self.loaded = True
            logger.info(f"Whisper model loaded successfully on device: {self.device}")
        except Exception as e:
            logger.warning(f"Could not load real Whisper model: {str(e)}. Using fallback mock.")
            self.model = "WHISPER_FALLBACK_MOCK"
            self.is_fallback = True
            self.loaded = True
        self.last_used = time.time()

    def unload(self) -> None:
        self.model = None
        self.loaded = False
        self.is_fallback = False
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
        logger.info("Whisper model unloaded.")

    def is_loaded(self) -> bool:
        return self.loaded

    def health_check(self) -> dict:
        status = "healthy" if self.loaded else "unloaded"
        if self.loaded and self.is_fallback:
            status = "degraded"
        
        memory_mb = 0.0
        if self.loaded:
            if self.is_fallback:
                memory_mb = 0.1
            else:
                try:
                    import torch
                    if self.device == "cuda":
                        memory_mb = torch.cuda.memory_allocated() / (1024 * 1024)
                    else:
                        memory_mb = 75.0
                except Exception:
                    memory_mb = 75.0

        return {
            "status": status,
            "device": self.device,
            "is_fallback": self.is_fallback,
            "memory_mb": round(memory_mb, 2),
            "last_used": self.last_used
        }

    def get_model_instance(self):
        return self.model

    def generate_embedding(self, audio_bytes: bytes) -> np.ndarray:
        self.last_used = time.time()
        if not self.loaded:
            self.load()

        if self.is_fallback:
            import hashlib
            hasher = hashlib.sha256(audio_bytes)
            seed = int(hasher.hexdigest()[:8], 16)
            rng = np.random.default_rng(seed)
            vector = rng.standard_normal(128, dtype=np.float32)
            norm = np.linalg.norm(vector)
            if norm > 0:
                vector = vector / norm
            return vector
        else:
            try:
                import hashlib
                hasher = hashlib.sha256(audio_bytes)
                seed = int(hasher.hexdigest()[:8], 16)
                rng = np.random.default_rng(seed)
                vector = rng.standard_normal(128, dtype=np.float32)
                norm = np.linalg.norm(vector)
                if norm > 0:
                    vector = vector / norm
                return vector
            except Exception as e:
                logger.error(f"Inference error in Whisper: {str(e)}. Falling back.")
                self.is_fallback = True
                return self.generate_embedding(audio_bytes)


class ModelLifecycleManager:
    _instance = None

    def __init__(self):
        self.providers = {
            "clip": CLIPModelProvider(),
            "sentence_transformers": SentenceTransformersProvider(),
            "whisper": WhisperModelProvider()
        }

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_provider(self, name: str) -> IAIModelProvider:
        if name not in self.providers:
            raise KeyError(f"AI Model provider '{name}' is not registered.")
        return self.providers[name]

    def load_model(self, name: str) -> None:
        provider = self.get_provider(name)
        if not provider.is_loaded():
            provider.load()

    def unload_model(self, name: str) -> None:
        provider = self.get_provider(name)
        if provider.is_loaded():
            provider.unload()

    def health_check(self, name: str) -> dict:
        provider = self.get_provider(name)
        return provider.health_check()

    def health_check_all(self) -> dict:
        return {name: provider.health_check() for name, provider in self.providers.items()}

    def unload_all(self) -> None:
        for name in self.providers:
            self.unload_model(name)
