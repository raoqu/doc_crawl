from . import BaseCrawler
import requests
from bs4 import BeautifulSoup
import html2text
import os
from urllib.parse import urlparse, urljoin
from .result import CrawlResult
import re

class DefaultCrawler(BaseCrawler):
    """Default crawler implementation"""
    
    def __init__(self):
        super().__init__()
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
    
    @property
    def name(self) -> str:
        return "default"

    def _extract_image_urls(self, soup) -> list[str]:
        # Find all images
        image_urls = []
        for img in soup.find_all('img'):
            src = img.get('src')
            if not src:
                continue
            image_urls.append(src)
        
        return image_urls
        
    def crawl(self, url: str, doc_path: str = None) -> CrawlResult:
        """Crawl a webpage and store its content"""
        try:
            # Download and parse HTML
            print("Fetching page", url)
            response = requests.get(url)
            if response.status_code != 200:
                return False, f"Failed to download page: {response.status_code}"
            
            ## FIXME: This does not work for dynamically loaded content
            raw_content = response.text
            soup = BeautifulSoup(raw_content, 'html.parser')
            
            # Get title
            title = soup.title.string if soup.title else "Untitled"
            
            # Download images first
            image_urls = self._extract_image_urls(soup)
            
            # Process HTML content
            html_content = str(soup)
            html_content = self._fix_relative_urls(html_content, url)
            
            # Convert to markdown and process images
            markdown_content = html2text.html2text(html_content)
            markdown_content = self._post_process_markdown(markdown_content)
            
            return CrawlResult(
                success=True,
                url=url, 
                title=title, 
                raw_content=raw_content,
                html=html_content,
                markdown=markdown_content,
                image_urls=image_urls,
            )
        except Exception as e:
            return CrawlResult(url=url,message=f"Error crawling page: {e}")

    def _fix_relative_urls(self, html_content, base_url):
        """Fix relative URLs in HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Fix links
        for a in soup.find_all('a', href=True):
            a['href'] = urljoin(base_url, a['href'])
        
        # Fix images
        for img in soup.find_all('img', src=True):
            img['src'] = urljoin(base_url, img['src'])
        
        return str(soup)
    
    def _post_process_markdown(self, content):
        """Clean up and format markdown content"""
        # Fix code block language hints
        content = re.sub(r'```(\w+)\n', r'```\1\n', content)
        
        # Clean up list formatting
        content = re.sub(r'\n\s*[-\*]\s', '\n* ', content)
        
        # Fix multiple blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content.strip()
