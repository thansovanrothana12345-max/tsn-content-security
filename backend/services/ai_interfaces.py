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
