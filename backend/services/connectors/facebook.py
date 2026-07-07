import os
import yt_dlp
import urllib.request
from urllib.parse import urlparse
from backend.services.connectors.base import BaseConnector

class FacebookConnector(BaseConnector):
    def validate(self, url: str) -> bool:
        domain = urlparse(url).netloc.lower()
        return any(p in domain for p in ["facebook.com", "fb.watch", "fb.com"])
        
    def extract_metadata(self, url: str) -> dict:
        parsed = urlparse(url)
        path = parsed.path
        
        is_ad_library = "/ads/library" in path
        platform = "Facebook Ad Library" if is_ad_library else "Facebook Post"
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                raw_date = info.get("upload_date", "")
                upload_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}" if len(raw_date) == 8 else raw_date or "Unknown Date"
                
                return {
                    "url": url,
                    "title": info.get("title") or (f"Facebook Ad #{path.split('id=')[-1]}" if is_ad_library else "Facebook Post"),
                    "uploader": info.get("uploader") or "Unknown Facebook Page",
                    "upload_date": upload_date,
                    "duration": info.get("duration", 0.0),
                    "thumbnail_url": info.get("thumbnail"),
                    "platform": platform
                }
        except Exception as e:
            ad_id = ""
            if "id=" in parsed.query:
                from urllib.parse import parse_qs
                ad_id = parse_qs(parsed.query).get("id", [""])[0]
                
            return {
                "url": url,
                "title": f"Facebook Ad Library Item #{ad_id}" if is_ad_library else "Facebook Post Link",
                "uploader": "Facebook Advertiser" if is_ad_library else "Facebook User",
                "upload_date": "N/A",
                "duration": 0.0,
                "thumbnail_url": None,
                "platform": platform,
                "error": str(e)
            }
            
    def download_asset(self, url: str, output_dir: str) -> str:
        os.makedirs(output_dir, exist_ok=True)
        ydl_opts = {
            'format': 'worst[ext=mp4]/worst',
            'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                if os.path.exists(filename):
                    return os.path.abspath(filename)
                
                video_id = info.get("id")
                if video_id:
                    for file in os.listdir(output_dir):
                        if file.startswith(video_id):
                            return os.path.abspath(os.path.join(output_dir, file))
                raise FileNotFoundError("Facebook video file missing.")
        except Exception as e:
            raise RuntimeError(f"Facebook download failed: {e}")
            
    def download_screenshot(self, url: str, output_dir: str, name_prefix: str) -> str:
        metadata = self.extract_metadata(url)
        thumb_url = metadata.get("thumbnail_url")
        if not thumb_url:
            return None
            
        os.makedirs(output_dir, exist_ok=True)
        ext = ".png" if ".png" in thumb_url else ".jpg"
        out_path = os.path.join(output_dir, f"{name_prefix}{ext}")
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            req = urllib.request.Request(thumb_url, headers=headers)
            with urllib.request.urlopen(req) as response:
                with open(out_path, 'wb') as out_file:
                    out_file.write(response.read())
            return os.path.abspath(out_path)
        except Exception as e:
            print(f"Facebook thumbnail download error: {e}")
            return None
