import logging
from datetime import datetime
from backend.database import get_db_connection

logger = logging.getLogger("tsn.asset_intelligence")

class AssetIntelligenceService:
    @staticmethod
    def register_license(original_id: int, license_type: str, licensee_name: str = None, allowed_platforms: list = None, geo_exclusions: list = None, expires_at: str = None) -> int:
        """Saves a license agreement matching an original reference asset ID."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # Verify original exists
            cursor.execute("SELECT id FROM originals WHERE id = ?;", (original_id,))
            if not cursor.fetchone():
                raise ValueError(f"Original asset reference not found with ID {original_id}")
                
            platforms_str = ",".join(allowed_platforms) if allowed_platforms else None
            exclusions_str = ",".join(geo_exclusions) if geo_exclusions else None
            
            cursor.execute("""
                INSERT INTO asset_licenses (original_id, license_type, licensee_name, allowed_platforms, geo_exclusions, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    license_type = excluded.license_type,
                    licensee_name = excluded.licensee_name,
                    allowed_platforms = excluded.allowed_platforms,
                    geo_exclusions = excluded.geo_exclusions,
                    expires_at = excluded.expires_at;
            """, (original_id, license_type, licensee_name, platforms_str, exclusions_str, expires_at))
            license_id = cursor.lastrowid
            conn.commit()
            return license_id
        finally:
            conn.close()

    @staticmethod
    def get_license(original_id: int) -> dict | None:
        """Fetches the license details matching an original asset ID."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, original_id, license_type, licensee_name, allowed_platforms, geo_exclusions, expires_at, created_at
                FROM asset_licenses
                WHERE original_id = ?;
            """, (original_id,))
            row = cursor.fetchone()
            if not row:
                return None
                
            row_dict = dict(row)
            row_dict["allowed_platforms"] = row_dict["allowed_platforms"].split(",") if row_dict["allowed_platforms"] else []
            row_dict["geo_exclusions"] = row_dict["geo_exclusions"].split(",") if row_dict["geo_exclusions"] else []
            return row_dict
        finally:
            conn.close()

    @staticmethod
    def check_infringement_validity(original_id: int, platform: str, region: str = None) -> bool:
        """
        Validates if sharing an asset on a target platform and region is an infringement.
        Returns:
            bool: True if it is an infringement (unauthorized), False if it is authorized.
        """
        license_info = AssetIntelligenceService.get_license(original_id)
        if not license_info:
            # If no license is registered, it is unauthorized by default
            return True
            
        # 1. Expiration check
        if license_info["expires_at"]:
            try:
                expiry_dt = datetime.fromisoformat(license_info["expires_at"])
                if datetime.utcnow() > expiry_dt:
                    logger.warning(f"License for Original {original_id} is expired.")
                    return True
            except ValueError:
                pass
                
        # 2. Platform permissions check
        # If allowed_platforms list is provided, confirm current platform is in it
        if license_info["allowed_platforms"]:
            allowed = [p.strip().lower() for p in license_info["allowed_platforms"]]
            if platform.strip().lower() not in allowed:
                logger.info(f"Platform {platform} is not allowed by license for Original {original_id}.")
                return True
                
        # 3. Geographic exclusions check
        # If geofence exclusions list is set, verify the region is not blocked
        if license_info["geo_exclusions"] and region:
            blocked = [r.strip().upper() for r in license_info["geo_exclusions"]]
            if region.strip().upper() in blocked:
                logger.info(f"Region {region} is explicitly blocked by geo-exclusions for Original {original_id}.")
                return True
                
        # If all checks pass, it is not an infringement (authorized share)
        return False
