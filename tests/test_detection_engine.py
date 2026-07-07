import unittest
import sys
import os

# Append project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.ai_interfaces import (
    ImageFingerprintInterface,
    VideoFingerprintInterface,
    AudioFingerprintInterface,
    ScanOrchestratorInterface,
    SimilarityEngineInterface
)
from backend.ai.fingerprint.service import FingerprintService
from backend.ai.services.orchestrator import AIServiceOrchestrator

class TestDetectionEngineInterfaces(unittest.TestCase):
    def test_fingerprint_service_inheritance(self):
        # Verify inheritance from fingerprint interfaces
        self.assertTrue(issubclass(FingerprintService, ImageFingerprintInterface))
        self.assertTrue(issubclass(FingerprintService, VideoFingerprintInterface))
        self.assertTrue(issubclass(FingerprintService, AudioFingerprintInterface))

    def test_orchestrator_inheritance(self):
        # Verify inheritance from orchestrator & similarity engine interfaces
        self.assertTrue(issubclass(AIServiceOrchestrator, ScanOrchestratorInterface))
        self.assertTrue(issubclass(AIServiceOrchestrator, SimilarityEngineInterface))
