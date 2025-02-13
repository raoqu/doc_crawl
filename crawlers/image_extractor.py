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

    def replace_markdown_images(self, markdown_content:str, local_images:dict[str, str], base_url=None):
        """Replace image URLs in markdown with local paths
        
        Args:
            markdown_content (str): Original markdown content
            local_images (dict): Mapping of original image URLs to local file paths
            base_url (str, optional): Base URL to resolve relative paths
            
        Returns:
            str: Markdown content with image URLs replaced by local paths
        """
        from urllib.parse import urljoin
        
        def get_full_url(url):
            """Convert relative URL to absolute URL"""
            if not url or not base_url:
                return url
            if url.startswith(('http://', 'https://', 'data:')):
                return url
            if url.startswith('//'):
                return 'https:' + url
            return urljoin(base_url, url)
        
        # First replace full URLs
        for image_url, local_path in local_images.items():
            local_image_path = f'images/{os.path.basename(local_path)}'
            # Replace both ![alt](url) and [alt](url) patterns
            markdown_content = markdown_content.replace(
                f'![]({image_url})',
                f'![]({local_image_path})'
            )
            markdown_content = markdown_content.replace(
                f']({image_url})',
                f']({local_image_path})'
            )
        
        # Then handle relative URLs if base_url is provided
        if base_url:
            import re
            # Find all markdown image patterns with relative URLs
            patterns = [
                r'!\[.*?\]\(((?!http|data:|//).*?)\)',  # ![alt](relative/path)
                r'\[.*?\]:\s*((?!http|data:|//).*?)(?:\s+".*?")?$'  # [ref]: relative/path
            ]
            
            for pattern in patterns:
                def replace_url(match):
                    relative_url = match.group(1)
                    full_url = get_full_url(relative_url)
                    if full_url in local_images:
                        local_path = local_images[full_url]
                        return match.group(0).replace(
                            relative_url,
                            f'images/{os.path.basename(local_path)}'
                        )
                    return match.group(0)
                
                markdown_content = re.sub(pattern, replace_url, markdown_content, flags=re.MULTILINE)
        
        return markdown_content