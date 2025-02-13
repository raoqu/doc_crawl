import re
from urllib.parse import urljoin
from typing import List, Set
import os

class ImageExtractor:
    """Extract image URLs from different content types"""
    
    def __init__(self):
        # Regex patterns for markdown image syntax
        self.md_image_patterns = [
            r'!\[.*?\]\((.*?)(?:\s+".*?")?\)',  # ![alt](url "title")
            r'!\[.*?\]\[(.*?)\]',               # ![alt][ref]
            r'\[.*?\]:\s*(.*?)(?:\s+".*?")?$'   # [ref]: url "title"
        ]
        self.md_local_image_patterns = [
            r'!\[.*?\]\((images/.*?)(?:\s+".*?")?\)',  # ![alt](url "title")
            r'!\[.*?\]\[(images/.*?)\]',               # ![alt][ref]
            r'\[.*?\]:\s*(images/.*?)(?:\s+".*?")?$'   # [ref]: url "title"
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


    def _get_full_url(self,url: str, base_url: str) -> str:
        """Convert relative URL to absolute URL"""
        if not url or not base_url:
            return url
        if url.startswith(('http://', 'https://', 'data:')):
            return url
        if url.startswith('//'):
            return 'https:' + url
        if base_url:
            return urljoin(base_url, url)
        return url

    def replace_markdown_images(self, markdown_content:str, local_images:dict[str, str], base_url=None):
        """Replace image URLs in markdown with local paths
        
        Args:
            markdown_content (str): Original markdown content
            local_images (dict): Mapping of original image URLs to local file paths
            base_url (str, optional): Base URL to resolve relative paths
            
        Returns:
            str: Markdown content with image URLs replaced by local paths
        """
        def _get_local_image_path(url) -> str:
            if url:
                for src in local_images:
                    if self._get_full_url(url, base_url) == self._get_full_url(src, base_url):
                        return local_images[src]
            return None
                        
        for pattern in self.md_image_patterns:
            matches = re.finditer(pattern, markdown_content, re.MULTILINE)
            for match in matches:
                url = match.group(1).strip()
                local_image_path = _get_local_image_path(url)
                if local_image_path:
                    markdown_content = markdown_content.replace(f'({url})', f'({local_image_path})')

        return markdown_content

    def restore_markdown_images(self, markdown: str, base_path: str) -> str:
        """Restore image URLs by replacing local paths with full URLs
        
        Args:
            markdown (str): Markdown content with local image paths
            base_path (str): Base path to use for constructing full URLs
            
        Returns:
            str: Markdown content with restored image URLs
            
        Example:
            Input:  ![alt](images/example.png)
            Output: ![alt](/view_image/path/to/doc/images/example.png)
        """
        if not base_path:
            return markdown

        for pattern in self.md_image_patterns:
            matches = re.finditer(pattern, markdown, re.MULTILINE)
            for match in matches:
                image_path = match.group(1).strip()
                view_path = f'/view_image/{base_path}/{image_path}'
                if view_path:
                    markdown = markdown.replace(f'({image_path})', f'({view_path})')

        return markdown