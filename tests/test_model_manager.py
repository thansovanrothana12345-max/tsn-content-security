import unittest
import os
import sys
import numpy as np
from PIL import Image

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.model_manager import ModelLifecycleManager, CLIPModelProvider, SentenceTransformersProvider, WhisperModelProvider

class TestModelManager(unittest.TestCase):
    def setUp(self):
        self.manager = ModelLifecycleManager.get_instance()
        self.manager.unload_all()

    def tearDown(self):
        self.manager.unload_all()

    def test_providers_registered(self):
        self.assertIn("clip", self.manager.providers)
        self.assertIn("sentence_transformers", self.manager.providers)
        self.assertIn("whisper", self.manager.providers)

    def test_clip_provider_lifecycle_and_fallback(self):
        provider = self.manager.get_provider("clip")
        self.assertFalse(provider.is_loaded())
        
        provider.load()
        self.assertTrue(provider.is_loaded())
        
        health = provider.health_check()
        self.assertIn("status", health)
        self.assertIn("device", health)
        self.assertIn("is_fallback", health)
        self.assertIn("memory_mb", health)
        
        img = Image.new("RGB", (100, 100), color="red")
        emb = provider.generate_embedding(img)
        self.assertEqual(len(emb), 512)
        self.assertTrue(np.allclose(np.linalg.norm(emb), 1.0))
        
        provider.unload()
        self.assertFalse(provider.is_loaded())

    def test_sentence_transformers_lifecycle_and_fallback(self):
        provider = self.manager.get_provider("sentence_transformers")
        self.assertFalse(provider.is_loaded())
        
        provider.load()
        self.assertTrue(provider.is_loaded())
        
        health = provider.health_check()
        self.assertTrue(health["is_fallback"])
        
        emb = provider.generate_embedding("Test copyright metadata check")
        self.assertEqual(len(emb), 768)
        self.assertTrue(np.allclose(np.linalg.norm(emb), 1.0))
        
        provider.unload()
        self.assertFalse(provider.is_loaded())

    def test_whisper_lifecycle_and_fallback(self):
        provider = self.manager.get_provider("whisper")
        self.assertFalse(provider.is_loaded())
        
        provider.load()
        self.assertTrue(provider.is_loaded())
        
        health = provider.health_check()
        self.assertTrue(health["is_fallback"])
        
        emb = provider.generate_embedding(b"mock_audio_sample_bytes_123")
        self.assertEqual(len(emb), 128)
        self.assertTrue(np.allclose(np.linalg.norm(emb), 1.0))
        
        provider.unload()
        self.assertFalse(provider.is_loaded())

    def test_manager_load_unload_all(self):
        self.manager.load_model("clip")
        self.assertTrue(self.manager.get_provider("clip").is_loaded())
        
        self.manager.unload_all()
        self.assertFalse(self.manager.get_provider("clip").is_loaded())
        self.assertFalse(self.manager.get_provider("sentence_transformers").is_loaded())
        self.assertFalse(self.manager.get_provider("whisper").is_loaded())

if __name__ == "__main__":
    unittest.main()
