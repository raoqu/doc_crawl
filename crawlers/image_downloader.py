import requests

class ImageDownloader:
    def __init__(self):
        pass

    def download_images(self, doc_url:str, image_urls:list[str], image_path:str) -> dict[str, str]:
        """Download all images from the page and return a mapping of URLs to local paths"""
        local_images = {}
        
        # Find all images
        for image_url in image_urls:
            # Download and save image
            local_path = self._download_image(doc_url, image_url, image_path)
            if local_path:
                local_images[image_url] = local_path
                
        return local_images
        
    def _download_image(self, doc_url, image_url, category_id):
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