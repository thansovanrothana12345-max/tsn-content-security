import yt_dlp
import os
import urllib.request
from urllib.parse import urlparse

def get_platform_from_url(url):
    """Detects the platform name from a given URL."""
    domain = urlparse(url).netloc.lower()
    if "youtube.com" in domain or "youtu.be" in domain:
        return "YouTube"
    elif "tiktok.com" in domain:
        return "TikTok"
    elif "facebook.com" in domain or "fb.watch" in domain:
        return "Facebook"
    elif "instagram.com" in domain:
        return "Instagram"
    else:
        return "Other"

def fetch_metadata(url):
    """
    Fetches video metadata using yt-dlp without downloading the video.
    Returns:
        dict: metadata containing title, uploader, upload_date, platform, duration, and thumbnail_url
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'extract_flat': False,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Normalize fields
            title = info.get("title", "Unknown Title")
            uploader = info.get("uploader") or info.get("channel") or info.get("creator") or "Unknown Creator"
            
            # Format upload date (YYYYMMDD to YYYY-MM-DD if possible)
            raw_date = info.get("upload_date", "")
            if len(raw_date) == 8:
                upload_date = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:]}"
            else:
                upload_date = raw_date or "Unknown Date"
                
            duration = info.get("duration", 0.0)
            
            # Get thumbnail
            thumbnail_url = info.get("thumbnail")
            if not thumbnail_url and info.get("thumbnails"):
                # Take the last/largest thumbnail
                thumbnail_url = info["thumbnails"][-1].get("url")
                
            return {
                "url": url,
                "title": title,
                "uploader": uploader,
                "upload_date": upload_date,
                "duration": duration,
                "thumbnail_url": thumbnail_url,
                "platform": get_platform_from_url(url)
            }
    except Exception as e:
        # Return partial metadata if yt-dlp fails
        print(f"Error fetching metadata via yt-dlp: {e}")
        return {
            "url": url,
            "title": "Unresolvable URL or Private Video",
            "uploader": "Unknown",
            "upload_date": "N/A",
            "duration": 0.0,
            "thumbnail_url": None,
            "platform": get_platform_from_url(url),
            "error": str(e)
        }

def download_video_for_analysis(url, output_dir):
    """
    Downloads a low-resolution version of the video (to save bandwidth and time)
    for fingerprinting.
    
    Returns:
        str: Absolute path to the downloaded video file.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # We download the worst quality mp4 format so it downloads in seconds
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
            # Sometimes extension changes, verify output file exists
            if os.path.exists(filename):
                return os.path.abspath(filename)
                
            # If not found directly, check output dir for matching video ID file
            video_id = info.get("id")
            if video_id:
                for file in os.listdir(output_dir):
                    if file.startswith(video_id):
                        return os.path.abspath(os.path.join(output_dir, file))
            raise FileNotFoundError("Could not find downloaded file.")
    except Exception as e:
        raise RuntimeError(f"Failed to download video: {e}")

def download_thumbnail(url, output_dir, name_prefix):
    """
    Downloads the thumbnail image from a thumbnail URL.
    Returns:
        str: Path to the downloaded image relative to static directory or absolute.
    """
    if not url:
        return None
        
    os.makedirs(output_dir, exist_ok=True)
    ext = ".jpg"
    if ".png" in url:
        ext = ".png"
    elif ".webp" in url:
        ext = ".webp"
        
    out_path = os.path.join(output_dir, f"{name_prefix}{ext}")
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as response:
            with open(out_path, 'wb') as out_file:
                out_file.write(response.read())
        return os.path.abspath(out_path)
    except Exception as e:
        print(f"Error downloading thumbnail: {e}")
        return None

if __name__ == "__main__":
    # Test fetch
    print(fetch_metadata("https://www.youtube.com/watch?v=dQw4w9WgXcQ"))
