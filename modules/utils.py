"""
Utility functions for Wayback Machine Downloader
"""

import logging
import re
from datetime import datetime


def setup_logging(verbose=False):
    """
    Setup logging configuration
    
    Args:
        verbose: Enable verbose logging
        
    Returns:
        Logger instance
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    # Create logger
    logger = logging.getLogger('wbdownloader')
    logger.setLevel(level)
    
    # Create console handler
    handler = logging.StreamHandler()
    handler.setLevel(level)
    
    # Create formatter
    if verbose:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        formatter = logging.Formatter('%(levelname)s: %(message)s')
    
    handler.setFormatter(formatter)
    
    # Add handler to logger
    logger.addHandler(handler)
    
    return logger


def validate_timestamp(timestamp):
    """
    Validate Wayback Machine timestamp format
    
    Args:
        timestamp: Timestamp string to validate
        
    Returns:
        Boolean indicating if timestamp is valid
    """
    # Check format: YYYYMMDDHHMMSS (14 digits)
    if not re.match(r'^\d{14}$', timestamp):
        return False
    
    # Try to parse as datetime
    try:
        datetime.strptime(timestamp, '%Y%m%d%H%M%S')
        return True
    except ValueError:
        return False


def validate_proxy_url(proxy_url):
    """
    Validate proxy URL format
    
    Args:
        proxy_url: Proxy URL to validate
        
    Returns:
        Boolean indicating if proxy URL is valid
    """
    if not proxy_url:
        return True  # None/empty is valid (no proxy)
    
    from urllib.parse import urlparse
    
    try:
        parsed = urlparse(proxy_url)
        
        # Check if it has a scheme
        if not parsed.scheme:
            return False
        
        # Check if scheme is supported
        if parsed.scheme.lower() not in ['http', 'https']:
            return False
        
        # Check if it has a hostname
        if not parsed.hostname:
            return False
        
        # Check if port is valid (if specified)
        if parsed.port is not None:
            if not (1 <= parsed.port <= 65535):
                return False
        
        return True
        
    except Exception:
        return False


def format_bytes(num_bytes):
    """
    Format bytes to human readable format
    
    Args:
        num_bytes: Number of bytes
        
    Returns:
        Formatted string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(num_bytes) < 1024.0:
            return f"{num_bytes:3.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


def sanitize_filename(filename):
    """
    Sanitize filename for safe file system storage
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Replace problematic characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f]', '', filename)
    
    # Limit length
    max_length = 255
    if len(filename) > max_length:
        name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
        if ext:
            name = name[:max_length - len(ext) - 1]
            filename = f"{name}.{ext}"
        else:
            filename = filename[:max_length]
    
    return filename


def is_valid_url(url):
    """
    Check if URL is valid
    
    Args:
        url: URL to validate
        
    Returns:
        Boolean indicating if URL is valid
    """
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE
    )
    return url_pattern.match(url) is not None


def extract_domain_from_url(url):
    """
    Extract domain name from URL
    
    Args:
        url: URL to extract domain from
        
    Returns:
        Domain name
    """
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path.split('/')[0]
    
    # Remove port if present
    if ':' in domain:
        domain = domain.split(':')[0]
    
    # Remove www. prefix if present
    if domain.startswith('www.'):
        domain = domain[4:]
    
    return domain


def is_same_domain(url1, url2):
    """
    Check if two URLs belong to the same domain
    
    Args:
        url1: First URL
        url2: Second URL
        
    Returns:
        Boolean indicating if URLs are from same domain
    """
    from urllib.parse import urlparse
    
    # Handle Wayback URLs - extract original URLs first
    from .wayback_api import WaybackAPI
    wayback_api = WaybackAPI()
    
    # Extract original URLs if they are Wayback URLs
    if 'web.archive.org' in url1:
        url1 = wayback_api.extract_original_url(url1)
    if 'web.archive.org' in url2:
        url2 = wayback_api.extract_original_url(url2)
    
    # Parse URLs
    parsed1 = urlparse(url1)
    parsed2 = urlparse(url2)
    
    # Get domains
    domain1 = parsed1.netloc.lower()
    domain2 = parsed2.netloc.lower()
    
    # Remove www prefix for comparison
    if domain1.startswith('www.'):
        domain1 = domain1[4:]
    if domain2.startswith('www.'):
        domain2 = domain2[4:]
    
    # Remove port for comparison
    domain1 = domain1.split(':')[0]
    domain2 = domain2.split(':')[0]
    
    return domain1 == domain2


def should_download_url(url, base_url, downloaded_urls=None):
    """
    Determine if a URL should be downloaded based on filtering rules
    
    Args:
        url: URL to check
        base_url: Base URL for domain comparison
        downloaded_urls: Set of already downloaded URLs
        
    Returns:
        Boolean indicating if URL should be downloaded
    """
    # Check if same domain
    if not is_same_domain(url, base_url):
        return False
    
    # Check if already downloaded
    if downloaded_urls and url in downloaded_urls:
        return False
    
    # Skip certain file extensions that are not HTML pages
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path = parsed.path.lower()
    
    # Common non-HTML extensions to skip
    skip_extensions = [
        '.jpg', '.jpeg', '.png', '.gif', '.svg', '.webp', '.ico',
        '.css', '.js', '.json', '.xml',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.zip', '.rar', '.tar', '.gz', '.7z',
        '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm',
        '.mp3', '.wav', '.ogg', '.m4a', '.flac',
        '.ttf', '.otf', '.woff', '.woff2', '.eot'
    ]
    
    for ext in skip_extensions:
        if path.endswith(ext):
            return False
    
    return True