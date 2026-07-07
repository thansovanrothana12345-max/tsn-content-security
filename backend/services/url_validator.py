import re
from urllib.parse import urlparse

def validate_and_parse_url(url: str) -> dict:
    """
    Validates the input URL and returns validation status, normalized platform,
    and sub-type details.
    
    Supported platforms:
    - YouTube
    - TikTok
    - Instagram
    - Facebook Post
    - Facebook Ad Library
    - Website
    """
    url = url.strip()
    if not url:
        return {"valid": False, "error": "URL cannot be empty."}
        
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            # Try prepending https:// if missing scheme
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
                parsed = urlparse(url)
            else:
                return {"valid": False, "error": "Invalid URL structure."}
    except Exception as e:
        return {"valid": False, "error": f"Failed to parse URL: {str(e)}"}
        
    domain = parsed.netloc.lower()
    path = parsed.path
    
    # 1. YouTube
    if any(p in domain for p in ["youtube.com", "youtu.be", "youtube-nocookie.com"]):
        if "youtu.be" in domain:
            video_id = path.strip("/")
            if len(video_id) >= 10:
                return {"valid": True, "platform": "YouTube", "type": "Video", "id": video_id, "url": url}
        else:
            if "/shorts/" in path:
                video_id = path.split("/shorts/")[-1].split("/")[0].split("?")[0]
                return {"valid": True, "platform": "YouTube", "type": "Shorts", "id": video_id, "url": url}
            elif "/watch" in path:
                from urllib.parse import parse_qs
                qs = parse_qs(parsed.query)
                if "v" in qs:
                    return {"valid": True, "platform": "YouTube", "type": "Video", "id": qs["v"][0], "url": url}
            elif "/embed/" in path:
                video_id = path.split("/embed/")[-1].split("/")[0].split("?")[0]
                return {"valid": True, "platform": "YouTube", "type": "Embed", "id": video_id, "url": url}
        
        # Generic fallback for youtube domain
        return {"valid": True, "platform": "YouTube", "type": "Other", "id": None, "url": url}
        
    # 2. TikTok
    elif "tiktok.com" in domain:
        if "vm.tiktok.com" in domain or "/t/" in path:
            return {"valid": True, "platform": "TikTok", "type": "ShortLink", "id": path.strip("/"), "url": url}
        else:
            video_match = re.search(r'/video/(\d+)', path)
            if video_match:
                return {"valid": True, "platform": "TikTok", "type": "Video", "id": video_match.group(1), "url": url}
        return {"valid": True, "platform": "TikTok", "type": "Other", "id": None, "url": url}
        
    # 3. Instagram
    elif "instagram.com" in domain:
        if "/p/" in path:
            post_id = path.split("/p/")[-1].strip("/")
            return {"valid": True, "platform": "Instagram", "type": "Post", "id": post_id, "url": url}
        elif "/reel/" in path:
            reel_id = path.split("/reel/")[-1].strip("/")
            return {"valid": True, "platform": "Instagram", "type": "Reel", "id": reel_id, "url": url}
        elif "/tv/" in path:
            tv_id = path.split("/tv/")[-1].strip("/")
            return {"valid": True, "platform": "Instagram", "type": "TV", "id": tv_id, "url": url}
        return {"valid": True, "platform": "Instagram", "type": "Other", "id": None, "url": url}
        
    # 4. Facebook Ad Library & Posts
    elif any(p in domain for p in ["facebook.com", "fb.watch", "fb.com"]):
        if "fb.watch" in domain:
            return {"valid": True, "platform": "Facebook Post", "type": "ShortWatch", "id": path.strip("/"), "url": url}
        elif "/ads/library" in path:
            from urllib.parse import parse_qs
            qs = parse_qs(parsed.query)
            ad_id = qs.get("id", [None])[0]
            return {"valid": True, "platform": "Facebook Ad Library", "type": "Ad", "id": ad_id, "url": url}
        elif "/posts/" in path:
            post_id = path.split("/posts/")[-1].split("/")[0].split("?")[0]
            return {"valid": True, "platform": "Facebook Post", "type": "Post", "id": post_id, "url": url}
        elif "/watch" in path or "video.php" in path:
            from urllib.parse import parse_qs
            qs = parse_qs(parsed.query)
            video_id = qs.get("v", [None])[0]
            return {"valid": True, "platform": "Facebook Post", "type": "Video", "id": video_id, "url": url}
            
        return {"valid": True, "platform": "Facebook Post", "type": "Other", "id": None, "url": url}
        
    # 5. General Web Sites / Websites
    elif domain:
        # A general valid website url
        return {"valid": True, "platform": "Website", "type": "WebPage", "id": None, "url": url}
        
    return {"valid": False, "error": "Invalid URL platform target."}
