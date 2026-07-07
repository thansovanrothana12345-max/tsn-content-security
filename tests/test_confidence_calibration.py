import unittest
import sys
import os

# Append project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import Config
from backend.fingerprint import ConfidenceScoringService

class TestConfidenceCalibration(unittest.TestCase):
    def setUp(self):
        # Save original config parameters
        self.orig_weights = getattr(Config, "CONFIDENCE_WEIGHTS_CALIBRATED", None)
        self.orig_a = getattr(Config, "CALIBRATION_SIGMOID_A", -12.0)
        self.orig_b = getattr(Config, "CALIBRATION_SIGMOID_B", 9.6)

    def tearDown(self):
        # Revert config parameters
        Config.CONFIDENCE_WEIGHTS_CALIBRATED = self.orig_weights
        Config.CALIBRATION_SIGMOID_A = self.orig_a
        Config.CALIBRATION_SIGMOID_B = self.orig_b

    def test_default_confidence_calibration(self):
        # Ensure default sigmoid maps 0.8 raw similarity to exactly 0.5 (Platt boundary)
        Config.CALIBRATION_SIGMOID_A = -12.0
        Config.CALIBRATION_SIGMOID_B = 9.6
        
        service = ConfidenceScoringService()
        
        # Test exact sigmoid boundary matching
        # When confidence calculation computes exactly 0.8 (raw), Platt scaling outputs exactly 0.5
        per_module_scores = {
            "video": 0.8,
            "audio": 0.8,
            "ocr": 0.8,
            "logo": 0.8,
            "metadata": 0.8
        }
        res = service.calculate_confidence(0.8, per_module_scores, [])
        self.assertEqual(res["overall_confidence"], 0.5)
        self.assertEqual(res["confidence_level"], "Medium")

    def test_high_low_confidence_calibration(self):
        Config.CALIBRATION_SIGMOID_A = -12.0
        Config.CALIBRATION_SIGMOID_B = 9.6
        service = ConfidenceScoringService()
        
        # High match (raw confidence = 1.0)
        high_res = service.calculate_confidence(1.0, {"video": 1.0}, [])
        # f(1.0) = 1 / (1 + exp(-12 * 1 + 9.6)) = 1 / (1 + exp(-2.4)) ~ 0.9168
        self.assertGreaterEqual(high_res["overall_confidence"], 0.9)
        self.assertEqual(high_res["confidence_level"], "High")
        
        # Low match (raw confidence = 0.5)
        low_res = service.calculate_confidence(0.5, {"video": 0.5}, [])
        # f(0.5) = 1 / (1 + exp(-12 * 0.5 + 9.6)) = 1 / (1 + exp(3.6)) ~ 0.026
        self.assertLessEqual(low_res["overall_confidence"], 0.1)
        self.assertEqual(low_res["confidence_level"], "Low")

    def test_dynamic_weights_configuration(self):
        # Set dynamic custom calibrated weights
        custom_weights = {
            "video": 0.50,
            "audio": 0.50
        }
        Config.CONFIDENCE_WEIGHTS_CALIBRATED = custom_weights
        
        service = ConfidenceScoringService()
        self.assertEqual(service.weights, custom_weights)
        
        # Calibrate with custom weights: video=1.0, audio=0.0 -> raw = 0.50
        # Check calculation with Platt calibration disabled (using dummy parameters that make it identity function: A=0, B=0)
        Config.CALIBRATION_SIGMOID_A = 0.0
        Config.CALIBRATION_SIGMOID_B = 0.0
        # If A=0, B=0, Platt sigmoid outputs 1 / (1 + exp(0)) = 0.5 always.
        # Let's verify Platt works with weights.
        
        # Let's restore standard calibration parameters
        Config.CALIBRATION_SIGMOID_A = -10.0
        Config.CALIBRATION_SIGMOID_B = 5.0
        # raw similarity = 0.5
        # f(0.5) = 1 / (1 + exp(-10 * 0.5 + 5.0)) = 1 / (1 + exp(0)) = 0.5
        res = service.calculate_confidence(0.5, {"video": 1.0, "audio": 0.0}, [])
        self.assertEqual(res["overall_confidence"], 0.5)

if __name__ == "__main__":
    unittest.main()
