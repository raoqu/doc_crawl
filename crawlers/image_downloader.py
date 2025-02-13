import requests
import os
import hashlib
import mimetypes
from urllib.parse import urlparse, urljoin

class ImageDownloader:
    def __init__(self):
        pass

    def download_images(self, doc_url:str, image_urls:list[str], images_path:str) -> dict[str, str]:
        """Download all images from the page and return a mapping of URLs to local paths"""
        local_images = {}
        
        # Find all images
        for image_url in image_urls:
            print("Downloading image", image_url)
            # Download and save image
            local_path = self._download_image(doc_url, image_url, images_path)
            if local_path:
                local_images[image_url] = local_path
                print("Downloaded image", image_url, "to", local_path)
                
        return local_images
        
    def _download_image(self, doc_url, image_url:str, image_path):
        """Download an image and save it locally"""
        try:
            # Handle relative URLs
            if image_url.startswith('//'):
                image_url = 'https:' + image_url
            elif not image_url.startswith(('http://', 'https://')):
                base_url = '/'.join(doc_url.split('/')[:-1])
                image_url = urljoin(base_url, image_url)
            
            # Download image
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Save the image and get its local path
            return self._save_image(image_url, response.content, image_path)
        except Exception as e:
            print(f"Error downloading image {url}: {str(e)}")
            return None
    

    def _save_image(self, image_url, image_data, image_path):
        """Save an image and return its local path relative to the document"""
        try:
            # Create images directory if it doesn't exist
            os.makedirs(image_path, exist_ok=True)
            
            # Generate a filename for the image
            image_name = hashlib.md5(image_url.encode()).hexdigest()[:12]
            
            # Try to get extension from URL first
            ext = os.path.splitext(image_url)[1].lower()
            if not ext or ext not in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']:
                # Try to guess from content type
                content_type = mimetypes.guess_type(image_url)[0]
                if content_type:
                    ext = mimetypes.guess_extension(content_type)
                
                # Default to .jpg if no valid extension found
                if not ext:
                    ext = '.jpg'
            
            markdown_dir = os.path.dirname(image_path)
            image_filename = f"{image_name}{ext}"
            image_path = os.path.join(image_path, image_filename)
            
            # Save the image
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            # Return relative path from markdown directory to image
            return os.path.relpath(image_path, markdown_dir)
        except Exception as e:
            print(f"Error saving image {image_url}: {e}")
            return None