import re
from urllib.parse import urljoin
from typing import List, Set

class ImageExtractor:
    """Extract image URLs from different content types"""
    
    def __init__(self):
        # Regex patterns for markdown image syntax
        self.md_image_patterns = [
            r'!\[.*?\]\((.*?)(?:\s+".*?")?\)',  # ![alt](url "title")
            r'!\[.*?\]\[(.*?)\]',               # ![alt][ref]
            r'\[.*?\]:\s*(.*?)(?:\s+".*?")?$'   # [ref]: url "title"
        ]
    
    def extract_from_markdown(self, content: str, base_url: str = None) -> Set[str]:
        """Extract image URLs from markdown content
        
        Args:
            content (str): Markdown content to parse
            base_url (str, optional): Base URL to resolve relative URLs
            
        Returns:
            Set[str]: Set of unique image URLs found in the content
        """
        image_urls = set()
        
        # Find all image URLs using regex patterns
        for pattern in self.md_image_patterns:
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                url = match.group(1).strip()
                if url:
                    # Handle relative URLs if base_url is provided
                    if base_url and not url.startswith(('http://', 'https://', 'data:')):
                        if url.startswith('//'):
                            url = 'https:' + url
                        else:
                            url = urljoin(base_url, url)
                    image_urls.add(url)
        
        return image_urls
    
    def extract_from_html(self, soup, base_url: str = None) -> Set[str]:
        """Extract image URLs from BeautifulSoup HTML content
        
        Args:
            soup: BeautifulSoup object
            base_url (str, optional): Base URL to resolve relative URLs
            
        Returns:
            Set[str]: Set of unique image URLs found in the content
        """
        image_urls = set()
        
        # Find all img tags
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                # Handle relative URLs if base_url is provided
                if base_url and not src.startswith(('http://', 'https://', 'data:')):
                    if src.startswith('//'):
                        src = 'https:' + src
                    else:
                        src = urljoin(base_url, src)
                image_urls.add(src)
                
        return image_urls