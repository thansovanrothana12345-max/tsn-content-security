from abc import ABC, abstractmethod

class VideoSimilarityInterface(ABC):
    @abstractmethod
    def compute_embedding(self, filepath: str) -> list:
        """Computes deep features/embeddings for a video file."""
        pass
        
    @abstractmethod
    def compare_embeddings(self, embedding_a: list, embedding_b: list) -> float:
        """Returns similarity score between 0.0 and 1.0."""
        pass

class ImageSimilarityInterface(ABC):
    @abstractmethod
    def compute_descriptor(self, filepath: str) -> list:
        """Computes image descriptors or visual embeddings."""
        pass
        
    @abstractmethod
    def compare_descriptors(self, desc_a: list, desc_b: list) -> float:
        """Returns similarity score between 0.0 and 1.0."""
        pass

class AudioSimilarityInterface(ABC):
    @abstractmethod
    def compute_spectrogram(self, filepath: str) -> list:
        """Computes audio spectrogram or acoustic fingerprints."""
        pass
        
    @abstractmethod
    def compare_spectrograms(self, spec_a: list, spec_b: list) -> float:
        """Returns similarity score between 0.0 and 1.0."""
        pass

class OCRInterface(ABC):
    @abstractmethod
    def extract_text(self, image_path: str) -> dict:
        """Extracts text content and bounding box coordinate metadata."""
        pass

class LogoDetectionInterface(ABC):
    @abstractmethod
    def detect_logos(self, image_path: str) -> list:
        """Detects registered brand logo entities in target images."""
        pass

class TextSimilarityInterface(ABC):
    @abstractmethod
    def compare_text(self, text_a: str, text_b: str) -> float:
        """Returns text similarity match score between 0.0 and 1.0."""
        pass

class ImageFingerprintInterface(ABC):
    @abstractmethod
    def fingerprint_image(self, pil_img) -> dict:
        """Computes perceptual hashes, embeddings, and feature descriptors for an image."""
        pass

class VideoFingerprintInterface(ABC):
    @abstractmethod
    def fingerprint_video(self, video_path: str, interval_sec: float = 1.0) -> list:
        """Processes video frames at intervals and generates visual sequence fingerprints."""
        pass

class AudioFingerprintInterface(ABC):
    @abstractmethod
    def fingerprint_audio(self, audio_path: str) -> dict:
        """Computes audio segment embeddings and metadata hashes."""
        pass

class SimilarityEngineInterface(ABC):
    @abstractmethod
    def check_similarity(self, case_id: int, source_id: int, source_type: str, target_id: int, target_type: str, match_types: list = None) -> dict:
        """Compares and scores similarity between two entities."""
        pass

class ScanOrchestratorInterface(ABC):
    @abstractmethod
    def ingest_fingerprint(self, case_id: int, entity_type: str, entity_id: int, file_path: str) -> int:
        """Processes a media file, generates fingerprints, and persists to registry."""
        pass

class IDetectionService(ABC):
    @abstractmethod
    def run_detection_check(self, case_id: int, evidence_id: int, asset_file: str) -> dict:
        """Executes full detection check pipeline on an asset file against originals."""
        pass


class IAIModelProvider(ABC):
    @abstractmethod
    def load(self) -> None:
        """Loads the model into system memory or CUDA VRAM."""
        pass

    @abstractmethod
    def unload(self) -> None:
        """Unloads the model to free resources."""
        pass

    @abstractmethod
    def is_loaded(self) -> bool:
        """Returns True if the model is currently loaded in memory."""
        pass

    @abstractmethod
    def health_check(self) -> dict:
        """Checks model provider state and returns status details."""
        pass

    @abstractmethod
    def get_model_instance(self):
        """Returns the raw model object instance (e.g. torch module)."""
        pass


class DependencyContainer:
    """Lightweight Service Locator for Dependency Injection."""
    _instance = None

    def __init__(self):
        self._services = {}

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(self, service_type, service_instance):
        self._services[service_type] = service_instance

    def resolve(self, service_type):
        if service_type not in self._services:
            raise KeyError(f"Service {service_type.__name__ if hasattr(service_type, '__name__') else service_type} not registered in container.")
        return self._services[service_type]

    @classmethod
    def reset(cls):
        cls._instance = None

