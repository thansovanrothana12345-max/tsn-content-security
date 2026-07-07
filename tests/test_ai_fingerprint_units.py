import unittest
import numpy as np
from PIL import Image
import json
import os
import sys

# Append project root to sys path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.ai.hashing.service import HashingService
from backend.ai.embeddings.service import EmbeddingsService
from backend.ai.similarity.service import SimilarityService
from backend.ai.detectors.service import DetectorsService

class TestAIFingerprintUnits(unittest.TestCase):
    def setUp(self):
        # Create a solid color dummy image for testing
        self.img = Image.new("RGB", (100, 100), color=(130, 84, 255))

    def test_hashing_service(self):
        # 1. Average Hash (aHash)
        ahash = HashingService.calculate_ahash(self.img)
        self.assertEqual(len(ahash), 16)
        # Ensure it is a valid hex string
        int(ahash, 16)
        
        # 2. Difference Hash (dHash)
        dhash = HashingService.calculate_dhash(self.img)
        self.assertEqual(len(dhash), 16)
        int(dhash, 16)
        
        # 3. Perceptual Hash (pHash)
        phash = HashingService.calculate_phash(self.img)
        self.assertEqual(len(phash), 16)
        int(phash, 16)

    def test_embeddings_service(self):
        # 1. Image Embedding
        img_emb = EmbeddingsService.generate_image_embedding(self.img)
        self.assertEqual(img_emb.shape, (512,))
        # Verify L2 normalization
        self.assertAlmostEqual(float(np.linalg.norm(img_emb)), 1.0, places=4)
        
        # 2. Text Embedding
        text_emb = EmbeddingsService.generate_text_embedding("Test copyright claim note")
        self.assertEqual(text_emb.shape, (768,))
        self.assertAlmostEqual(float(np.linalg.norm(text_emb)), 1.0, places=4)
        
        # 3. Text Embedding Determinism
        text_emb2 = EmbeddingsService.generate_text_embedding("Test copyright claim note")
        np.testing.assert_array_almost_equal(text_emb, text_emb2)

    def test_similarity_service(self):
        # 1. Hamming distance
        h1 = "ffffffffffffffff"
        h2 = "0000000000000000"
        dist = SimilarityService.hamming_distance(h1, h2)
        self.assertEqual(dist, 64)
        
        sim = SimilarityService.normalized_hamming_similarity(h1, h2)
        self.assertEqual(sim, 0.0)
        
        sim_self = SimilarityService.normalized_hamming_similarity(h1, h1)
        self.assertEqual(sim_self, 1.0)
        
        # 2. Cosine similarity
        v1 = np.array([1.0, 0.0, 0.0])
        v2 = np.array([0.0, 1.0, 0.0])
        sim_cos = SimilarityService.cosine_similarity(v1, v2)
        self.assertEqual(sim_cos, 0.0)
        
        sim_cos_self = SimilarityService.cosine_similarity(v1, v1)
        self.assertAlmostEqual(sim_cos_self, 1.0, places=5)
        
        # 3. Hybrid score
        score = SimilarityService.calculate_hybrid_score(0.8, 0.9, weight_hash=0.4)
        self.assertAlmostEqual(score, 0.86, places=5)

    def test_detectors_service(self):
        kp_json, desc_bytes = DetectorsService.extract_orb_features(self.img)
        self.assertIsInstance(kp_json, str)
        kp_list = json.loads(kp_json)
        self.assertIsInstance(kp_list, list)
        self.assertIsInstance(desc_bytes, bytes)
        
        # Deserialize test
        desc_arr = DetectorsService.deserialize_descriptors(desc_bytes)
        if desc_arr is not None:
            self.assertEqual(desc_arr.ndim, 2)
            self.assertEqual(desc_arr.shape[1], 32)

if __name__ == "__main__":
    unittest.main()
