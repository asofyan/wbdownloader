"""
Wayback Machine API interactions
"""

from urllib.parse import quote


class WaybackAPI:
    """Handle Wayback Machine API interactions"""
    
    BASE_URL = "https://web.archive.org/web"
    
    def __init__(self):
        pass
    
    def construct_url(self, original_url, timestamp):
        """
        Construct a Wayback Machine URL from original URL and timestamp
        
        Args:
            original_url: The original website URL
            timestamp: Wayback Machine timestamp (YYYYMMDDHHMMSS)
            
        Returns:
            Complete Wayback Machine URL
        """
        # Ensure URL has protocol
        if not original_url.startswith(('http://', 'https://')):
            original_url = 'http://' + original_url
        
        # Construct Wayback URL
        wayback_url = f"{self.BASE_URL}/{timestamp}/{original_url}"
        return wayback_url
    
    def extract_original_url(self, wayback_url):
        """
        Extract the original URL from a Wayback Machine URL
        
        Args:
            wayback_url: Full Wayback Machine URL
            
        Returns:
            Original URL
        """
        # Remove Wayback prefix
        if wayback_url.startswith(self.BASE_URL):
            # Find the timestamp part (14 digits after /web/)
            parts = wayback_url.split('/')
            for i, part in enumerate(parts):
                if part == 'web' and i + 2 < len(parts):
                    # Skip 'web' and timestamp
                    original_url = '/'.join(parts[i+2:])
                    # Ensure protocol
                    if not original_url.startswith(('http://', 'https://')):
                        original_url = 'http://' + original_url
                    return original_url
        
        return wayback_url
    
    def convert_to_wayback_url(self, url, base_wayback_url):
        """
        Convert a regular URL to Wayback Machine URL using the same timestamp
        
        Args:
            url: Regular URL to convert
            base_wayback_url: Reference Wayback URL to extract timestamp
            
        Returns:
            Wayback Machine URL
        """
        # Extract timestamp from base URL
        timestamp = self.extract_timestamp(base_wayback_url)
        if not timestamp:
            return url
        
        # Handle already-wayback URLs
        if url.startswith(self.BASE_URL):
            # Clean it first to remove modifiers
            return self.clean_wayback_url(url)
        
        # Handle protocol-relative URLs
        if url.startswith('//'):
            url = 'https:' + url
        
        # Construct new Wayback URL
        return self.construct_url(url, timestamp)
    
    def extract_timestamp(self, wayback_url):
        """
        Extract timestamp from Wayback Machine URL
        
        Args:
            wayback_url: Wayback Machine URL
            
        Returns:
            Timestamp string or None
        """
        if self.BASE_URL in wayback_url:
            # Use regex to find timestamp (14 digits) even with modifiers
            import re
            match = re.search(r'/web/(\d{14})', wayback_url)
            if match:
                return match.group(1)
        return None
    
    def clean_wayback_url(self, url):
        """
        Clean and normalize Wayback Machine URL
        
        Args:
            url: URL to clean
            
        Returns:
            Cleaned URL
        """
        # Remove any Wayback toolbar parameters
        if '_' in url and '/http' in url:
            # Handle URLs like /web/20240417160532_/http://example.com
            url = url.replace('_/', '/')
        
        # Remove im_ or js_ or cs_ modifiers
        # These appear after the timestamp
        import re
        # Pattern to match timestamp followed by modifier
        pattern = r'(/web/\d{14})(im_|js_|cs_|if_|id_|oe_|)(/)'        
        url = re.sub(pattern, r'\1\3', url)
        
        return url