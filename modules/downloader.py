"""
Async downloader for efficient file downloading
"""

import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from urllib.parse import urlparse, unquote
import mimetypes
from tqdm.asyncio import tqdm
import time
import random
from datetime import datetime
import platform

from .wayback_api import WaybackAPI


class AsyncDownloader:
    """Handle asynchronous file downloads"""
    
    # List of realistic user agents to rotate through
    USER_AGENTS = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0'
    ]
    
    def __init__(self, output_dir, max_concurrent=1, logger=None, proxy=None):
        self.output_dir = Path(output_dir)
        self.max_concurrent = max_concurrent
        self.logger = logger
        self.proxy = proxy
        self.wayback_api = WaybackAPI()
        self.session = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
        # Statistics
        self.downloaded = 0
        self.failed = 0
        self.skipped = 0
        
        # Request tracking for delay management
        self.last_request_time = 0
        self.request_count = 0
    
    async def __aenter__(self):
        """Async context manager entry"""
        timeout = aiohttp.ClientTimeout(total=60, connect=30, sock_read=30)
        
        # Log proxy usage
        if self.proxy:
            if self.logger:
                self.logger.info(f"Using proxy: {self.proxy}")
        
        # Select a random user agent
        user_agent = random.choice(self.USER_AGENTS)
        
        # Build browser-like headers
        headers = {
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # Configure connection pooling and SSL
        connector = aiohttp.TCPConnector(
            limit=100,  # Total connection pool limit
            limit_per_host=30,  # Per-host connection limit
            ttl_dns_cache=300,  # DNS cache timeout
            enable_cleanup_closed=True
        )
        
        # Create session with cookie jar
        self.session = aiohttp.ClientSession(
            timeout=timeout,
            headers=headers,
            connector=connector,
            cookie_jar=aiohttp.CookieJar()
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def _apply_request_delay(self):
        """Apply smart delay between requests to avoid bot detection"""
        current_time = time.time()
        self.request_count += 1
        
        # Base delay range (0.5 to 2 seconds)
        min_delay = 0.5
        max_delay = 2.0
        
        # Every 10 requests, add a longer pause
        if self.request_count % 10 == 0:
            min_delay = 2.0
            max_delay = 5.0
            if self.logger:
                self.logger.debug(f"Applied longer pause after {self.request_count} requests")
        
        # Calculate time since last request
        time_since_last = current_time - self.last_request_time
        
        # Generate random delay
        target_delay = random.uniform(min_delay, max_delay)
        
        # Only sleep if we haven't waited long enough
        if time_since_last < target_delay:
            sleep_time = target_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def download_file(self, wayback_url, original_url, is_main=False, save=True, force_download=False):
        """
        Download a single file
        
        Args:
            wayback_url: Wayback Machine URL
            original_url: Original URL for determining file path
            is_main: Whether this is the main HTML file
            save: Whether to save the file to disk
            force_download: Force download even if file exists
            
        Returns:
            Tuple of (content, file_path) or (None, None) on failure
        """
        try:
            # Determine file path first to check if it exists
            file_path = None
            if save:
                # We need to get the file path to check existence
                # Create a temporary response object for path determination
                file_path = self._determine_file_path(original_url, is_main, None)
                
                # Check if file already exists and we don't want to force download
                if not force_download and file_path.exists():
                    self.skipped += 1
                    if self.logger:
                        self.logger.debug(f"File already exists, skipping download: {file_path}")
                    
                    # Read existing file content
                    content = await self._read_existing_file(file_path)
                    if content is not None:
                        return content, file_path
                    else:
                        if self.logger:
                            self.logger.warning(f"Failed to read existing file: {file_path}")
                        # Continue with download if reading fails
            
            async with self.semaphore:
                # Apply delay before request
                await self._apply_request_delay()
                
                # Retry logic for rate limiting and network errors
                max_retries = 5
                base_delay = 2.0
                
                for attempt in range(max_retries + 1):
                    try:
                        # Rotate user agent for each retry
                        headers = {'User-Agent': random.choice(self.USER_AGENTS)}
                        
                        # Add referer header to look more natural
                        if not is_main:
                            headers['Referer'] = 'https://web.archive.org/'
                        
                        async with self.session.get(wayback_url, proxy=self.proxy, headers=headers) as response:
                            if response.status == 429:
                                # Rate limited - wait and retry with exponential backoff
                                if attempt < max_retries:
                                    # Exponential backoff with jitter
                                    delay = base_delay * (2 ** attempt) + random.uniform(0, 3)
                                    if self.logger:
                                        self.logger.warning(f"Rate limited (429), retrying in {delay:.1f}s: {wayback_url}")
                                    await asyncio.sleep(delay)
                                    continue
                                else:
                                    if self.logger:
                                        self.logger.warning(f"Failed to download after {max_retries} retries (429): {wayback_url}")
                                    self.failed += 1
                                    return None, None
                            
                            if response.status != 200:
                                if self.logger:
                                    self.logger.warning(f"Failed to download {wayback_url}: {response.status}")
                                self.failed += 1
                                return None, None
                            
                            # Success - break out of retry loop
                            break
                    
                    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                        if attempt < max_retries:
                            # Exponential backoff with jitter
                            delay = base_delay * (2 ** attempt) + random.uniform(0, 3)
                            if self.logger:
                                # Check if it's a proxy-related error
                                error_msg = str(e).lower()
                                if 'proxy' in error_msg or 'tunnel' in error_msg:
                                    self.logger.warning(f"Proxy error, retrying in {delay:.1f}s: {wayback_url} - {str(e)}")
                                else:
                                    self.logger.warning(f"Network error, retrying in {delay:.1f}s: {wayback_url} - {str(e)}")
                            await asyncio.sleep(delay)
                            continue
                        else:
                            if self.logger:
                                error_msg = str(e).lower()
                                if 'proxy' in error_msg or 'tunnel' in error_msg:
                                    self.logger.error(f"Proxy connection failed after {max_retries} retries: {wayback_url} - {str(e)}")
                                    self.logger.error("Please check your proxy configuration and connectivity")
                                else:
                                    self.logger.warning(f"Failed to download after {max_retries} retries: {wayback_url} - {str(e)}")
                            self.failed += 1
                            return None, None
                    
                content = await response.read()
                
                # Decode text content
                if response.content_type and 'text' in response.content_type:
                    try:
                        content = content.decode('utf-8')
                    except UnicodeDecodeError:
                        # Try with latin-1 as fallback
                        try:
                            content = content.decode('latin-1')
                        except:
                            # Keep as bytes if decoding fails
                            pass
                
                if not save:
                    return content, None
                
                # Determine file path if not already set
                if file_path is None:
                    file_path = self._determine_file_path(original_url, is_main, response)
                
                # Create directory
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save file
                if isinstance(content, str):
                    async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                        await f.write(content)
                else:
                    async with aiofiles.open(file_path, 'wb') as f:
                        await f.write(content)
                
                self.downloaded += 1
                if self.logger:
                    self.logger.debug(f"Downloaded: {file_path}")
                
                return content, file_path
                    
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Unexpected error downloading {wayback_url}: {str(e)}")
            self.failed += 1
            return None, None
    
    async def download_assets(self, assets, sequential=False):
        """
        Download multiple assets concurrently or sequentially
        
        Args:
            assets: List of asset dictionaries
            sequential: If True, download assets one by one
        """
        # Filter out None assets
        valid_assets = [a for a in assets if a is not None]
        
        # Create progress bar
        progress_bar = tqdm(
            total=len(valid_assets),
            desc="Downloading assets",
            unit="files"
        )
        
        if sequential:
            # Download assets sequentially
            for asset in valid_assets:
                await self._download_asset_with_progress(
                    asset['wayback_url'],
                    asset['original_url'],
                    progress_bar
                )
        else:
            # Create download tasks for concurrent execution
            tasks = []
            for asset in valid_assets:
                task = self._download_asset_with_progress(
                    asset['wayback_url'],
                    asset['original_url'],
                    progress_bar
                )
                tasks.append(task)
            
            # Execute downloads concurrently
            await asyncio.gather(*tasks, return_exceptions=True)
        
        progress_bar.close()
        
        # Log statistics
        if self.logger:
            self.logger.info(f"Download statistics:")
            self.logger.info(f"  Downloaded: {self.downloaded}")
            self.logger.info(f"  Failed: {self.failed}")
            self.logger.info(f"  Skipped: {self.skipped}")
    
    async def _download_asset_with_progress(self, wayback_url, original_url, progress_bar):
        """Download asset and update progress bar"""
        try:
            await self.download_file(wayback_url, original_url)
            # Delay is now handled inside download_file method
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Failed to download {wayback_url}: {str(e)}")
        finally:
            progress_bar.update(1)
    
    def _determine_file_path(self, url, is_main, response=None):
        """
        Determine local file path for URL
        
        Args:
            url: Original URL
            is_main: Whether this is the main file
            response: aiohttp response object (optional)
            
        Returns:
            Path object for local file
        """
        # Parse URL
        parsed = urlparse(url)
        
        # Get path components
        path = unquote(parsed.path)
        if not path or path == '/':
            path = '/index.html'
        elif path.endswith('/'):
            path += 'index.html'
        
        # Remove leading slash
        if path.startswith('/'):
            path = path[1:]
        
        # Handle query parameters in filename
        if parsed.query:
            # Replace special characters
            query_safe = parsed.query.replace('&', '_').replace('=', '_')
            base, ext = Path(path).stem, Path(path).suffix
            path = f"{base}_{query_safe}{ext}"
        
        # Ensure file has extension
        file_path = Path(path)
        if not file_path.suffix:
            # Try to determine from content-type if response is available
            if response:
                content_type = response.headers.get('content-type', '').split(';')[0]
                ext = mimetypes.guess_extension(content_type)
                if ext:
                    path += ext
                else:
                    # Default to .html for text content
                    if 'text' in content_type:
                        path += '.html'
            else:
                # Default to .html if no response object
                path += '.html'
        
        # Construct full path
        full_path = self.output_dir / path
        
        return full_path
    
    async def _read_existing_file(self, file_path):
        """
        Read existing file content
        
        Args:
            file_path: Path to the existing file
            
        Returns:
            File content as string or bytes, or None if failed
        """
        try:
            # Try to read as text first (for HTML files)
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    return content
            except UnicodeDecodeError:
                # Try with latin-1 as fallback
                try:
                    async with aiofiles.open(file_path, 'r', encoding='latin-1') as f:
                        content = await f.read()
                        return content
                except:
                    # Read as binary if text reading fails
                    async with aiofiles.open(file_path, 'rb') as f:
                        content = await f.read()
                        return content
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Failed to read existing file {file_path}: {str(e)}")
            return None
    
    def scan_existing_files(self):
        """
        Scan the output directory for existing files and return their URLs
        
        Returns:
            Set of URLs that have already been downloaded based on existing files
        """
        existing_urls = set()
        
        if not self.output_dir.exists():
            return existing_urls
        
        # Find all HTML files in the output directory
        for html_file in self.output_dir.rglob('*.html'):
            try:
                # Convert file path back to URL
                relative_path = html_file.relative_to(self.output_dir)
                
                # Skip if it's an index file in root (main page)
                if relative_path.name == 'index.html' and len(relative_path.parts) == 1:
                    continue
                
                # Reconstruct the URL from the file path
                url_path = str(relative_path)
                if url_path.endswith('/index.html'):
                    url_path = url_path[:-11]  # Remove /index.html
                elif url_path.endswith('.html'):
                    url_path = url_path[:-5]   # Remove .html
                
                # This is a simplified reconstruction - in practice, we'd need
                # to be more sophisticated about converting file paths back to URLs
                # For now, we'll just mark that we have HTML files
                if self.logger:
                    self.logger.debug(f"Found existing HTML file: {html_file}")
                    
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Error processing existing file {html_file}: {str(e)}")
        
        return existing_urls