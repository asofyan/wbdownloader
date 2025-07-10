"""
HTML and CSS parser for extracting assets
"""

import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from .wayback_api import WaybackAPI


class AssetParser:
    """Parse HTML and CSS to extract asset URLs"""
    
    def __init__(self):
        self.wayback_api = WaybackAPI()
        
        # Asset patterns in CSS
        self.css_url_pattern = re.compile(
            r'url\s*\(\s*["\']?([^"\'()]+)["\']?\s*\)',
            re.IGNORECASE
        )
        
        # Common asset extensions
        self.asset_extensions = {
            'image': ['.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico', '.bmp'],
            'css': ['.css'],
            'js': ['.js'],
            'font': ['.woff', '.woff2', '.ttf', '.otf', '.eot'],
            'video': ['.mp4', '.webm', '.ogg', '.avi', '.mov'],
            'audio': ['.mp3', '.wav', '.ogg', '.m4a'],
            'document': ['.pdf', '.doc', '.docx', '.xls', '.xlsx']
        }
    
    def extract_assets(self, html_content, base_url):
        """
        Extract all asset URLs from HTML content
        
        Args:
            html_content: HTML string
            base_url: Base URL for resolving relative URLs
            
        Returns:
            List of asset dictionaries with URLs and types
        """
        assets = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract stylesheets
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href:
                assets.append(self._create_asset_dict(href, base_url, 'css'))
        
        # Extract scripts
        for script in soup.find_all('script', src=True):
            src = script.get('src')
            if src:
                assets.append(self._create_asset_dict(src, base_url, 'js'))
        
        # Extract images
        for img in soup.find_all('img'):
            src = img.get('src')
            if src:
                assets.append(self._create_asset_dict(src, base_url, 'image'))
            # Also get srcset
            srcset = img.get('srcset')
            if srcset:
                for src_item in srcset.split(','):
                    src_url = src_item.strip().split(' ')[0]
                    if src_url:
                        assets.append(self._create_asset_dict(src_url, base_url, 'image'))
        
        # Extract favicons and other link resources
        for link in soup.find_all('link'):
            if link.get('rel') and 'icon' in str(link.get('rel')):
                href = link.get('href')
                if href:
                    assets.append(self._create_asset_dict(href, base_url, 'image'))
        
        # Extract video sources
        for video in soup.find_all(['video', 'source']):
            src = video.get('src')
            if src:
                assets.append(self._create_asset_dict(src, base_url, 'video'))
        
        # Extract audio sources
        for audio in soup.find_all(['audio', 'source']):
            src = audio.get('src')
            if src:
                assets.append(self._create_asset_dict(src, base_url, 'audio'))
        
        # Extract inline style URLs
        for element in soup.find_all(style=True):
            style = element.get('style', '')
            css_assets = self._extract_urls_from_css(style, base_url)
            assets.extend(css_assets)
        
        # Extract meta property images (Open Graph, Twitter Cards)
        for meta in soup.find_all('meta'):
            if meta.get('property') in ['og:image', 'twitter:image']:
                content = meta.get('content')
                if content:
                    assets.append(self._create_asset_dict(content, base_url, 'image'))
        
        return assets
    
    def extract_links(self, html_content, base_url):
        """
        Extract all hyperlinks from HTML content
        
        Args:
            html_content: HTML string
            base_url: Base URL for resolving relative URLs
            
        Returns:
            List of link dictionaries with URLs
        """
        links = []
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract all anchor tags with href
        for anchor in soup.find_all('a', href=True):
            href = anchor.get('href')
            if href:
                # Skip anchors, javascript, mailto, tel, etc.
                if href.startswith(('#', 'javascript:', 'mailto:', 'tel:', 'ftp:', 'data:')):
                    continue
                
                # Create link dict similar to assets
                link_dict = self._create_link_dict(href, base_url)
                if link_dict:
                    links.append(link_dict)
        
        # Remove duplicates
        unique_links = []
        seen_urls = set()
        for link in links:
            if link['wayback_url'] not in seen_urls:
                seen_urls.add(link['wayback_url'])
                unique_links.append(link)
        
        return unique_links
    
    def _create_link_dict(self, url, base_url):
        """
        Create link dictionary with normalized URLs
        
        Args:
            url: Link URL (relative or absolute)
            base_url: Base URL for resolution
            
        Returns:
            Link dictionary or None if invalid
        """
        # Clean the URL
        url = url.strip()
        
        # Skip empty URLs
        if not url:
            return None
        
        # Handle Wayback-specific URL modifications
        if url.startswith('/web/') and 'http' in url:
            # This is likely a Wayback URL
            wayback_base = self.wayback_api.BASE_URL
            url = wayback_base + url
        
        # Resolve relative URLs
        if not url.startswith(('http://', 'https://', '//')):
            # For Wayback URLs, we need to resolve against the original URL
            original_base = self.wayback_api.extract_original_url(base_url)
            resolved_url = urljoin(original_base, url)
        else:
            resolved_url = url
        
        # Handle protocol-relative URLs
        if resolved_url.startswith('//'):
            resolved_url = 'https:' + resolved_url
        
        # Convert to Wayback URL if needed
        wayback_url = self.wayback_api.convert_to_wayback_url(resolved_url, base_url)
        wayback_url = self.wayback_api.clean_wayback_url(wayback_url)
        
        return {
            'original_url': resolved_url,
            'wayback_url': wayback_url,
            'type': 'link'
        }
    
    def extract_css_assets(self, css_content, base_url):
        """
        Extract asset URLs from CSS content
        
        Args:
            css_content: CSS string
            base_url: Base URL for resolving relative URLs
            
        Returns:
            List of asset dictionaries
        """
        return self._extract_urls_from_css(css_content, base_url)
    
    def _extract_urls_from_css(self, css_content, base_url):
        """
        Extract URLs from CSS content using regex
        
        Args:
            css_content: CSS string
            base_url: Base URL for resolving relative URLs
            
        Returns:
            List of asset dictionaries
        """
        assets = []
        
        # Find all url() declarations
        matches = self.css_url_pattern.findall(css_content)
        
        for url in matches:
            # Skip data URLs and empty URLs
            if url.startswith('data:') or not url.strip():
                continue
            
            # Determine asset type
            asset_type = self._determine_asset_type(url)
            assets.append(self._create_asset_dict(url, base_url, asset_type))
        
        return assets
    
    def _create_asset_dict(self, url, base_url, asset_type):
        """
        Create asset dictionary with normalized URLs
        
        Args:
            url: Asset URL (relative or absolute)
            base_url: Base URL for resolution
            asset_type: Type of asset
            
        Returns:
            Asset dictionary
        """
        # Clean the URL
        url = url.strip()
        
        # Skip data URLs
        if url.startswith('data:'):
            return None
        
        # Handle Wayback-specific URL modifications
        if url.startswith('/web/') and 'http' in url:
            # This is likely a Wayback URL
            wayback_base = self.wayback_api.BASE_URL
            url = wayback_base + url
        
        # Resolve relative URLs
        if not url.startswith(('http://', 'https://', '//')):
            # For Wayback URLs, we need to resolve against the original URL
            original_base = self.wayback_api.extract_original_url(base_url)
            resolved_url = urljoin(original_base, url)
        else:
            resolved_url = url
        
        # Handle protocol-relative URLs
        if resolved_url.startswith('//'):
            resolved_url = 'https:' + resolved_url
        
        # Convert to Wayback URL if needed
        wayback_url = self.wayback_api.convert_to_wayback_url(resolved_url, base_url)
        wayback_url = self.wayback_api.clean_wayback_url(wayback_url)
        
        return {
            'original_url': resolved_url,
            'wayback_url': wayback_url,
            'type': asset_type
        }
    
    def _determine_asset_type(self, url):
        """
        Determine asset type from URL
        
        Args:
            url: Asset URL
            
        Returns:
            Asset type string
        """
        url_lower = url.lower()
        
        for asset_type, extensions in self.asset_extensions.items():
            for ext in extensions:
                if ext in url_lower:
                    return asset_type
        
        # Default to 'other'
        return 'other'