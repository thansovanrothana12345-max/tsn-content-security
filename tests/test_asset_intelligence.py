import unittest
import sys
import os
from datetime import datetime, timedelta

# Append project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db_connection, init_db
from backend.services.asset_intelligence import AssetIntelligenceService

class TestAssetIntelligence(unittest.TestCase):
    def setUp(self):
        init_db()
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cases;")
        cursor.execute("DELETE FROM originals;")
        cursor.execute("INSERT INTO cases (id, title, description, status, priority) VALUES (888, 'Case 888', 'Desc', 'Active', 'Medium');")
        cursor.execute("""
            INSERT INTO originals (id, case_id, filename, file_uuid, storage_provider, filesize, duration, fingerprint_json)
            VALUES (101, 888, 'original_video.mp4', 'uuid_101', 'local', 1024, 10.0, '[]');
        """)
        conn.commit()
        conn.close()

    def test_licensing_and_platform_compliance(self):
        # 1. Register a license that allows sharing ONLY on YouTube and TikTok
        AssetIntelligenceService.register_license(
            original_id=101,
            license_type="Exclusive",
            licensee_name="Lic Corp",
            allowed_platforms=["YouTube", "TikTok"],
            geo_exclusions=["US", "CA"]
        )
        
        # 2. Check if matching on YouTube is an infringement - should be FALSE (authorized)
        is_infringement_yt = AssetIntelligenceService.check_infringement_validity(101, "YouTube")
        self.assertFalse(is_infringement_yt)
        
        # 3. Check if matching on Facebook is an infringement - should be TRUE (unauthorized)
        is_infringement_fb = AssetIntelligenceService.check_infringement_validity(101, "Facebook")
        self.assertTrue(is_infringement_fb)
        
        # 4. Check if matching on YouTube in US region is an infringement - should be TRUE (blocked geo region US)
        is_infringement_us = AssetIntelligenceService.check_infringement_validity(101, "YouTube", "US")
        self.assertTrue(is_infringement_us)
        
        # 5. Check if matching on YouTube in FR region is an infringement - should be FALSE (authorized region FR)
        is_infringement_fr = AssetIntelligenceService.check_infringement_validity(101, "YouTube", "FR")
        self.assertFalse(is_infringement_fr)

    def test_expired_license_infringement(self):
        # Register a license that has expired
        past_date = (datetime.utcnow() - timedelta(days=2)).isoformat()
        AssetIntelligenceService.register_license(
            original_id=101,
            license_type="Exclusive",
            expires_at=past_date
        )
        
        # Should be an infringement because the license expired
        is_infringement = AssetIntelligenceService.check_infringement_validity(101, "YouTube")
        self.assertTrue(is_infringement)

if __name__ == "__main__":
    unittest.main()
