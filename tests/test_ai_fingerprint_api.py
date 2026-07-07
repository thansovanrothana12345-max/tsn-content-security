import unittest
import json
import io
import os
import sys
from fastapi.testclient import TestClient

# Append root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app import app
from backend.database import get_db_connection

class TestAIFingerprintAPIs(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        # Login to obtain auth token
        login_res = self.client.post("/api/v1/auth/login", json={
            "email": "admin@example.com",
            "password": "AdminPassword123"
        })
        self.assertEqual(login_res.status_code, 200, "Admin login failed")
        self.token = login_res.json()["token"]
        self.headers = {"Authorization": f"Bearer {self.token}"}
        
        # Create a test case folder
        case_res = self.client.post("/api/v1/cases", headers=self.headers, json={
            "title": "Test Integration Case",
            "description": "Integration check",
            "priority": "Medium",
            "client_name": "AI Test Corp",
            "platform": "Other"
        })
        self.assertEqual(case_res.status_code, 201, "Case creation failed")
        self.case_id = case_res.json()["id"]

    def test_end_to_end_fingerprint_pipeline(self):
        # 1. Test image fingerprint upload
        img_bytes = io.BytesIO()
        from PIL import Image
        Image.new("RGB", (50, 50), color=(255, 0, 0)).save(img_bytes, format="JPEG")
        img_bytes.seek(0)
        
        img_upload_res = self.client.post(
            "/api/v2/fingerprint/image",
            headers=self.headers,
            data={"case_id": self.case_id},
            files={"file": ("test_ui_upload.jpg", img_bytes, "image/jpeg")}
        )
        self.assertEqual(img_upload_res.status_code, 201, f"Image upload failed: {img_upload_res.text}")
        img_data = img_upload_res.json()
        self.assertIn("id", img_data)
        self.assertIn("phash", img_data)
        self.assertEqual(img_data["embeddings_status"], "Generated (CLIP-512)")
        
        fp_id = img_data["id"]
        evidence_id = img_data["evidence_id"]
        
        # 2. Test GET fingerprint details
        get_fp_res = self.client.get(f"/api/v2/fingerprint/{fp_id}", headers=self.headers)
        self.assertEqual(get_fp_res.status_code, 200)
        fp_details = get_fp_res.json()
        self.assertEqual(fp_details["id"], fp_id)
        self.assertIn("hashes", fp_details)
        self.assertIn("embeddings", fp_details)
        
        # 3. Test GET fingerprint details by entity
        get_ent_res = self.client.get(f"/api/v2/fingerprint/entity/evidence/{evidence_id}", headers=self.headers)
        self.assertEqual(get_ent_res.status_code, 200)
        ent_details = get_ent_res.json()
        self.assertEqual(ent_details["id"], fp_id)
        
        # 4. Test video fingerprint async queueing
        vid_bytes = io.BytesIO(b"RIFF....AVI LIST....") # mock minimal AVI format to satisfy simple checks
        vid_upload_res = self.client.post(
            "/api/v2/fingerprint/video",
            headers=self.headers,
            data={"case_id": self.case_id},
            files={"file": ("test_movie.avi", vid_bytes, "video/avi")}
        )
        self.assertEqual(vid_upload_res.status_code, 202)
        vid_data = vid_upload_res.json()
        self.assertIn("job_id", vid_data)
        self.assertEqual(vid_data["status"], "Queued")
        
        # 5. Test audio fingerprint upload
        aud_bytes = io.BytesIO(b"ID3v2....MP3....")
        aud_upload_res = self.client.post(
            "/api/v2/fingerprint/audio",
            headers=self.headers,
            data={"case_id": self.case_id},
            files={"file": ("song.mp3", aud_bytes, "audio/mpeg")}
        )
        self.assertEqual(aud_upload_res.status_code, 201)
        aud_data = aud_upload_res.json()
        self.assertIn("id", aud_data)
        
        # 6. Create a mock original reference entry manually to verify similarity matching
        import uuid
        unique_uuid = f"uuid-ref-{uuid.uuid4()}"
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO originals (case_id, filename, file_uuid, storage_provider, filesize, duration)
            VALUES (?, 'ref_image.jpg', ?, 'local', 100, 0.0)
        """, (self.case_id, unique_uuid))
        ref_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Ingest fingerprint for the original
        from backend.ai.services.orchestrator import AIServiceOrchestrator
        # Write dummy reference file to disk
        dummy_ref_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dummy_ref.jpg")
        Image.new("RGB", (50, 50), color=(255, 0, 0)).save(dummy_ref_path, format="JPEG")
        try:
            ref_fp_id = AIServiceOrchestrator.ingest_fingerprint(self.case_id, "original", ref_id, dummy_ref_path)
            
            # Run similarity checks between uploaded evidence and original reference
            sim_res = self.client.post(
                "/api/v2/similarity/check",
                headers=self.headers,
                json={
                    "case_id": self.case_id,
                    "source_id": evidence_id,
                    "source_type": "evidence",
                    "target_id": ref_id,
                    "target_type": "original",
                    "match_types": ["perceptual_hash", "embedding"]
                }
            )
            self.assertEqual(sim_res.status_code, 200)
            sim_data = sim_res.json()
            self.assertIn("overall_score", sim_data)
            self.assertIn("decision", sim_data)
            self.assertGreaterEqual(sim_data["overall_score"], 0.8) # Red image similarity to Red image should be high!
            
            # 7. Query similarity history list
            hist_res = self.client.get(f"/api/v2/similarity/history?case_id={self.case_id}", headers=self.headers)
            self.assertEqual(hist_res.status_code, 200)
            hist_list = hist_res.json()
            self.assertGreater(len(hist_list), 0)
            self.assertEqual(hist_list[0]["source_id"], evidence_id)
            self.assertEqual(hist_list[0]["target_id"], ref_id)
            
        finally:
            if os.path.exists(dummy_ref_path):
                os.remove(dummy_ref_path)

if __name__ == "__main__":
    unittest.main()
