from urllib.parse import urlparse
from backend.services.connectors.youtube import YouTubeConnector
from backend.services.connectors.tiktok import TikTokConnector
from backend.services.connectors.instagram import InstagramConnector
from backend.services.connectors.facebook import FacebookConnector
from backend.services.connectors.website import WebsiteConnector
from backend.services.connectors.base import BaseConnector

def get_connector_for_url(url: str) -> BaseConnector:
    """
    Returns the appropriate connector instance for a given URL.
    """
    youtube = YouTubeConnector()
    if youtube.validate(url):
        return youtube
        
    tiktok = TikTokConnector()
    if tiktok.validate(url):
        return tiktok
        
    instagram = InstagramConnector()
    if instagram.validate(url):
        return instagram
        
    facebook = FacebookConnector()
    if facebook.validate(url):
        return facebook
        
    website = WebsiteConnector()
    if website.validate(url):
        return website
        
    raise ValueError(f"No connector registered for URL: {url}")
