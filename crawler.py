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
        
    def _download_image(self, doc_url, url, category_id):
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
            return self.doc_storage.save_image(doc_url, url, response.content, category_id)
        except Exception as e:
            # print(f"Error downloading image {url}: {str(e)}")
            return None
    
    def _download_images(self, doc_url, soup, category_id):
        """Download all images from the page and return a mapping of URLs to local paths"""
        local_images = {}
        
        # Find all images
        for img in soup.find_all('img'):
            src = img.get('src')
            if not src:
                continue
                
            # Download and save image
            local_path = self._download_image(doc_url, src, category_id)
            if local_path:
                local_images[src] = local_path
                
        return local_images
    
    def _replace_markdown_images(self, markdown_content, local_images):
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
        """Crawl a webpage and store its content"""
        try:
            # Download and parse HTML
            response = requests.get(url)
            if response.status_code != 200:
                return False, f"Failed to download page: {response.status_code}"
            
            raw_content = response.text
            soup = BeautifulSoup(raw_content, 'html.parser')
            
            # Get title
            title = soup.title.string if soup.title else url
            
            # Download images first
            local_images = self._download_images(url, soup, category_id)
            
            # Process HTML content
            html_content = str(soup)
            html_content = self._fix_relative_urls(html_content, url)
            
            # Convert to markdown and process images
            markdown_content = html2text.html2text(html_content)
            markdown_content = self._post_process_markdown(markdown_content)
            markdown_content = self._replace_markdown_images(markdown_content, local_images)
            
            # Store the document with category
            self.doc_storage.add_document(
                url=url, 
                title=title, 
                raw_content=raw_content,
                markdown=markdown_content,
                category_id=category_id
            )
            
            return True, "Success"
        except Exception as e:
            return False, f"Error crawling page: {e}"
    
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
