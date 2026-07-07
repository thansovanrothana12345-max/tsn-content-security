from abc import ABC, abstractmethod

class BaseConnector(ABC):
    @abstractmethod
    def validate(self, url: str) -> bool:
        """Validates if the URL is supported by this connector."""
        pass
        
    @abstractmethod
    def extract_metadata(self, url: str) -> dict:
        """
        Fetches metadata from the URL.
        Returns a dict: {title, uploader, upload_date, duration, thumbnail_url, platform}
        """
        pass
        
    @abstractmethod
    def download_asset(self, url: str, output_dir: str) -> str:
        """
        Downloads a low-resolution asset/video for fingerprint matching.
        Returns the absolute filepath to the downloaded file.
        """
        pass
        
    @abstractmethod
    def download_screenshot(self, url: str, output_dir: str, name_prefix: str) -> str:
        """
        Downloads the thumbnail/screenshot image of the target leak.
        Returns the absolute filepath to the saved image.
        """
        pass
