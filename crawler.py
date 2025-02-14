import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urlparse, urljoin
import html2text
from typing import Tuple
from concurrent.futures import ThreadPoolExecutor
from crawlers import ImageDownloader, ImageExtractor
from crawlers.manager import CrawlerManager
from DocumentStorage import DocumentStorage
import logging

logger = logging.getLogger(__name__)

image_extractor = ImageExtractor()
image_downloader = ImageDownloader()

class Crawler:
    def __init__(self, doc_storage:DocumentStorage):
        """Initialize the crawler with document storage"""
        self.doc_storage = doc_storage
        self.manager = CrawlerManager()
        self.html_converter = html2text.HTML2Text()
        # Configure html2text for better conversion
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.body_width = 0
        self.html_converter.protect_links = True
        self.html_converter.unicode_snob = True
        self.html_converter.mark_code = True
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def crawl(self, url: str, category_id: int) -> Tuple[bool, str, int]:
        """Crawl a URL and store the content
        
        Args:
            url: URL to crawl
            category_id: Category ID to store the document under
            
        Returns:
            Tuple[bool, str, int]: (success, error_message, document_id)
        """
        try:
            # Get crawler for this URL
            crawler = self.manager.get_crawler(url)
            if not crawler:
                return False, "No crawler available for this URL", None
            
            doc_path = self.doc_storage.get_document_path(url, category_id)
            images_path = os.path.join(doc_path, 'images')
            
            # Crawl the URL
            result = crawler.crawl(url, doc_path)
            if not result.success:
                logger.info(result.json())
                return False, result.message, -1

            # Download images
            local_images = image_downloader.download_images(url, result.image_urls, images_path)

            # Replace image URLs in markdown
            markdown_content = image_extractor.replace_markdown_images(result.markdown, local_images, url)
            
            # Store the document with category
            doc_id = self.doc_storage.add_document(
                url=url,
                title=result.title,
                raw_content=result.html,
                markdown=markdown_content,
                category_id=category_id
            )
            
            if doc_id<0:
                return False, "Failed to add document", None
            elif doc_id==0:
                return False, "Document already exists", None
            else:
                return True, "Success", doc_id
        except Exception as e:
            logger.error(f"Error during crawl: {e}", exc_info=True)
            return False, str(e), None