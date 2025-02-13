import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urlparse, urljoin
import html2text
from typing import Tuple
from concurrent.futures import ThreadPoolExecutor
from crawlers.image_downloader import ImageDownloader
from crawlers.manager import CrawlerManager
from DocumentStorage import DocumentStorage
import logging

logger = logging.getLogger(__name__)

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

    def crawl(self, url, category_id=None):
        """Crawl a webpage and store its content"""
        try:
            logger.info(f"Starting crawl for URL: {url} with category: {category_id}")
            crawler = self.manager.get_crawler(url)
            if not crawler:
                logger.error("No suitable crawler found")
                return False, "No suitable crawler found"

            doc_path = self.doc_storage.get_document_path(url, category_id)
            
            result = crawler.crawl(url, doc_path)
            print(doc_path)
            print(result.json())

            # Download images
            images_path = os.path.join(doc_path, 'images')
            local_images = ImageDownloader().download_images(url, result.image_urls, images_path)

            # Replace image URLs in markdown
            markdown_content = self._replace_markdown_images(result.markdown, local_images)
            
            # Store the document with category
            self.doc_storage.add_document(
                url=url, 
                title=result.title, 
                raw_content=result.html,
                markdown=markdown_content,
                category_id=category_id
            )
            
            return True, "Success"
        except Exception as e:
            logger.error(f"Error during crawl: {e}", exc_info=True)
            return False, str(e)
    
    def _replace_markdown_images(self, markdown_content:str, local_images:dict[str, str]):
        """Replace image URLs in markdown with local paths"""
        for url, local_path in local_images.items():
            # Handle both markdown image syntaxes
            markdown_content = markdown_content.replace(
                f'![]({url})', 
                f'![](images/{os.path.basename(local_path)})'
            )
            markdown_content = markdown_content.replace(
                f']({url})', 
                f'](images/{os.path.basename(local_path)})'
            )
        return markdown_content