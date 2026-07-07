import unittest
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch

# Append project root to sys path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.detection_service import DetectionService

class TestDetectionServiceUnit(unittest.TestCase):
    def setUp(self):
        self.service = DetectionService()

    def test_run_detection_check_missing_file_throws_error(self):
        with self.assertRaises(FileNotFoundError):
            self.service.run_detection_check(case_id=1, evidence_id=1, asset_file="non_existent_file.mov")

    @patch("backend.services.detection_service.get_db_connection")
    @patch("backend.services.detection_service.AIServiceOrchestrator.ingest_fingerprint")
    @patch("backend.services.detection_service.AIServiceOrchestrator.check_similarity")
    def test_run_detection_check_success_score(self, mock_sim, mock_ingest, mock_db):
        # Stub SQLite connections
        mock_conn = MagicMock()
        mock_cursor = mock_conn.cursor.return_value
        
        # Stub originals rows
        mock_cursor.fetchall.return_value = [(101,)]
        mock_cursor.fetchone.side_effect = [
            (None,), # Fetch fingerprint_json for original
            None    # Fetch phash/ahash/dhash
        ]
        mock_db.return_value = mock_conn

        # Stub check similarity return
        mock_sim.return_value = {
            "overall_score": 0.92,
            "matches": {"perceptual_hash": 0.94},
            "decision": "Match Copy"
        }

        # Create temporary placeholder file
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name

        try:
            res = self.service.run_detection_check(case_id=10, evidence_id=20, asset_file=tmp_path)
            
            # Assert schema matching DetectionResult structure
            self.assertEqual(res["evidence_id"], 20)
            self.assertEqual(res["case_id"], 10)
            self.assertEqual(res["overall_similarity"], 0.92)
            self.assertIn("modality_scores", res)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

if __name__ == "__main__":
    unittest.main()
