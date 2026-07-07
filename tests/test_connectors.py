import pytest
from backend.services.url_validator import validate_and_parse_url
from backend.services.connectors import get_connector_for_url
from backend.services.connectors.youtube import YouTubeConnector
from backend.services.connectors.tiktok import TikTokConnector
from backend.services.connectors.instagram import InstagramConnector
from backend.services.connectors.facebook import FacebookConnector
from backend.services.connectors.website import WebsiteConnector

def test_url_validation_youtube():
    res = validate_and_parse_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert res["valid"] is True
    assert res["platform"] == "YouTube"
    assert res["type"] == "Video"
    assert res["id"] == "dQw4w9WgXcQ"

    res_short = validate_and_parse_url("https://youtu.be/dQw4w9WgXcQ")
    assert res_short["valid"] is True
    assert res_short["platform"] == "YouTube"
    assert res_short["id"] == "dQw4w9WgXcQ"

    res_shorts = validate_and_parse_url("https://www.youtube.com/shorts/dQw4w9WgXcQ")
    assert res_shorts["valid"] is True
    assert res_shorts["platform"] == "YouTube"
    assert res_shorts["type"] == "Shorts"
    assert res_shorts["id"] == "dQw4w9WgXcQ"

def test_url_validation_tiktok():
    res = validate_and_parse_url("https://www.tiktok.com/@username/video/7123456789012345678")
    assert res["valid"] is True
    assert res["platform"] == "TikTok"
    assert res["type"] == "Video"
    assert res["id"] == "7123456789012345678"

    res_short = validate_and_parse_url("https://vm.tiktok.com/ZMYx4Yyyy/")
    assert res_short["valid"] is True
    assert res_short["platform"] == "TikTok"
    assert res_short["type"] == "ShortLink"

def test_url_validation_instagram():
    res = validate_and_parse_url("https://www.instagram.com/p/CoF123abc/")
    assert res["valid"] is True
    assert res["platform"] == "Instagram"
    assert res["type"] == "Post"
    assert res["id"] == "CoF123abc"

    res_reel = validate_and_parse_url("https://www.instagram.com/reel/CoF123Reel/")
    assert res_reel["valid"] is True
    assert res_reel["platform"] == "Instagram"
    assert res_reel["type"] == "Reel"
    assert res_reel["id"] == "CoF123Reel"

def test_url_validation_facebook():
    res_ad = validate_and_parse_url("https://www.facebook.com/ads/library/?id=987654321")
    assert res_ad["valid"] is True
    assert res_ad["platform"] == "Facebook Ad Library"
    assert res_ad["type"] == "Ad"
    assert res_ad["id"] == "987654321"

    res_post = validate_and_parse_url("https://www.facebook.com/permalink.php?story_fbid=12345&id=6789")
    assert res_post["valid"] is True
    assert res_post["platform"] == "Facebook Post"

def test_url_validation_website():
    res = validate_and_parse_url("https://news.google.com/topstories")
    assert res["valid"] is True
    assert res["platform"] == "Website"

def test_url_validation_invalid():
    res = validate_and_parse_url("")
    assert res["valid"] is False
    assert "empty" in res["error"].lower()

def test_connector_resolver():
    conn_yt = get_connector_for_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert isinstance(conn_yt, YouTubeConnector)

    conn_tt = get_connector_for_url("https://www.tiktok.com/@username/video/12345")
    assert isinstance(conn_tt, TikTokConnector)

    conn_ig = get_connector_for_url("https://www.instagram.com/p/12345/")
    assert isinstance(conn_ig, InstagramConnector)

    conn_fb = get_connector_for_url("https://www.facebook.com/ads/library/?id=123")
    assert isinstance(conn_fb, FacebookConnector)

    conn_web = get_connector_for_url("https://www.wikipedia.org/")
    assert isinstance(conn_web, WebsiteConnector)
