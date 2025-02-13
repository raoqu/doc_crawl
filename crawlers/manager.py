import yaml
from typing import Dict, Type
from . import BaseCrawler
from .default import DefaultCrawler
import importlib
import traceback
import re

class CrawlerManager:
    """Manages crawler plugins and their configuration"""
    
    def __init__(self, config_path='config.yaml'):
        self.crawlers = []
        self.config_path = config_path
        self._load_config()
        
    def _load_config(self):
        """Load crawler configurations from YAML file"""
        try:
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Clear existing crawlers
            self.crawlers = []
            
            # Load crawler configurations
            for crawler_config in config.get('crawlers', []):
                domain = crawler_config.get('domain')
                crawler_type = crawler_config.get('type', 'default')
                
                if not domain:
                    continue
                    
                # Convert domain to regex pattern
                pattern = domain.replace('.', r'\.').replace('*', r'.*')
                self.crawlers.append({
                    'pattern': re.compile(pattern),
                    'type': crawler_type
                })
                
        except Exception as e:
            print(f"Error loading crawler config: {e}")
            # Use default crawler as fallback
            self.crawlers = []

    def get_crawler_by_type(self, crawler_type: str) -> BaseCrawler:
        if crawler_type != 'default':
            try:
                # Try to import custom crawler
                module = importlib.import_module(f'.{crawler_type}', 'crawlers')
                crawler_class = getattr(module, f"{crawler_type.capitalize()}Crawler")
                return crawler_class()
            except Exception as e:
                print(f"Error loading custom crawler {crawler_type}: {e}")
                traceback.print_exc()
                # Fall back to default crawler
                return DefaultCrawler()
        else:
            return DefaultCrawler()
            
    def get_crawler(self, url: str) -> BaseCrawler:
        """Get appropriate crawler for the given URL"""
        # Find matching crawler configuration
        for crawler in self.crawlers:
            if crawler['pattern'].search(url):
                crawler_type = crawler['type']
                return self.get_crawler_by_type(crawler_type)
                    
        # Use default crawler if no match found
        return DefaultCrawler()
