import requests
from bs4 import BeautifulSoup
import os
from urllib.parse import urlparse, urljoin
import html2text
import re
from concurrent.futures import ThreadPoolExecutor
import mimetypes

class Crawler:
    def __init__(self, doc_storage):
        self.doc_storage = doc_storage
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
        
    def _download_image(self, doc_url, url):
        """Download an image and save it locally"""
        try:
            # Handle relative URLs
            if url.startswith('//'):
                url = 'https:' + url
            elif not url.startswith(('http://', 'https://')):
                base_url = '/'.join(doc_url.split('/')[:-1])
                url = urljoin(base_url, url)
            
            # Download image
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            # Save the image and get its local path
            return self.doc_storage.save_image(doc_url, url, response.content)
        except Exception as e:
            # print(f"Error downloading image {url}: {str(e)}")
            return None
    
    def _download_images(self, doc_url, soup):
        """Download all images from the page and return a mapping of URLs to local paths"""
        local_images = {}
        
        # Find all images
        for img in soup.find_all('img'):
            src = img.get('src')
            if not src:
                continue
                
            # Download and save image
            local_path = self._download_image(doc_url, src)
            if local_path:
                local_images[src] = local_path
                
        return local_images
    
    def _replace_markdown_images(self, markdown_content, local_images):
        """Replace image URLs in markdown with local paths"""
        for url, local_path in local_images.items():
            # Handle different URL formats
            patterns = [
                url,
                url.replace(':', r'\:'),  # Escaped colons
                url.replace('/', r'\/'),  # Escaped slashes
            ]
            
            for pattern in patterns:
                # Replace both markdown and HTML image references
                markdown_content = re.sub(
                    rf'!\[([^\]]*)\]\({pattern}\)',
                    rf'![\1]({local_path})',
                    markdown_content
                )
                markdown_content = re.sub(
                    rf'<img[^>]*src=["\'{pattern}"\'[^>]*>',
                    rf'<img src="{local_path}">',
                    markdown_content
                )
                
        return markdown_content
    
    def _extract_title(self, html_content):
        """Extract title from HTML content"""
        soup = BeautifulSoup(html_content, 'html.parser')
        if soup.title:
            return soup.title.string.strip()
        
        # Try h1 if no title tag
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
            
        return "Untitled"
    
    def _post_process_markdown(self, content):
        """Clean up and format markdown content"""
        # Fix code block language hints
        content = re.sub(r'```(\w+)\n', r'```\1\n', content)
        
        # Clean up list formatting
        content = re.sub(r'\n\s*[-\*]\s', '\n* ', content)
        
        # Fix multiple blank lines
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        return content.strip()

    def crawl(self, url, category_id=None):
        """
        Crawl a URL and store its content
        
        Args:
            url (str): URL to crawl
            category_id (int, optional): Category ID to assign to the document
        """
        try:
            # Fetch the webpage
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            html_content = response.text
            
            # Parse HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup.find_all(['script', 'style', 'iframe', 'noscript']):
                element.decompose()
            
            # Download images
            local_images = self._download_images(url, soup)
            
            # Extract title from HTML
            title = self._extract_title(html_content)
            
            # Process main content
            main_content = soup.body
            
            # Fix relative URLs in the HTML
            html_content = self._fix_relative_urls(html_content, url)
            
            # Convert to markdown and process images
            markdown_content = self.html_converter.handle(html_content)
            markdown_content = self._post_process_markdown(markdown_content)
            # markdown_content = self._replace_markdown_images(markdown_content, local_images)
            
            # Store the document
            self.doc_storage.add_document(url=url, 
                                        title=title, 
                                        markdown=markdown_content,
                                        category_id=category_id)
            
            # Get domain from URL
            domain = urlparse(url).netloc
            
            return {
                'success': True,
                'title': title,
                'url': url,
                'domain': domain,
                'content': markdown_content,
                'image_count': len(local_images)
            }
            
        except Exception as e:
            import traceback
            print(f"Error crawling {url}:")
            print(traceback.format_exc())
            return {
                'success': False,
                'error': str(e),
                'url': url
            }
    
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
