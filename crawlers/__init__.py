from abc import ABC, abstractmethod
from .result import CrawlResult
from .image_extractor import ImageExtractor
from .image_downloader import ImageDownloader

class BaseCrawler(ABC):
    """Base class for all crawler plugins"""
    
    def __init__(self):
        pass

    @abstractmethod
    def crawl(self, url: str, doc_path: str = None) -> CrawlResult:
        """Crawl the given URL and return (success, obj)"""
        pass
        
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this crawler type"""
        pass
