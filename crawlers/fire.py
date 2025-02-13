# Install with pip install firecrawl-py
import os
import logging
from . import BaseCrawler
from .result import CrawlResult
from firecrawl import FirecrawlApp
from pydantic import BaseModel, Field

FIRECRAWLER_API_KEY = os.getenv('FIRECRAWLER_API_KEY')

logger = logging.getLogger(__name__)

class Metadata(BaseModel):
    title: str = Field (default="")

class ScrapeResult(BaseModel):
    metadata: Metadata = Field (default=Metadata())
    markdown: str = Field (default="")
    links: list[str] = Field (default_factory=list)

class FireCrawler(BaseCrawler):
    """Default crawler implementation"""
    
    def __init__(self):
        super().__init__()
        if not FIRECRAWLER_API_KEY:
            raise ValueError("FIRECRAWLER_API_KEY not set")

    @property
    def name(self) -> str:
        return "fire"

    def crawl(self, url: str, doc_path: str = None) -> CrawlResult:
        """Crawl a webpage and store its content"""
        try:
            app = FirecrawlApp(api_key=FIRECRAWLER_API_KEY)
            response = app.scrape_url(url=url, params={
                'formats': [ 'markdown', 'links' ],
            })
            print(response)
            scrape_result = ScrapeResult.parse_obj(response)
            return CrawlResult(
                success=False,
                url=url, 
                title=scrape_result.metadata.title,
                html="",
                markdown=scrape_result.markdown,
                link_urls=scrape_result.links
            )
        except Exception as e:
            logger.error(f"Firecrawler - Error crawling {url}: {e}", exc_info=True)
            return CrawlResult(False, f"Error crawling {url}: {e}")