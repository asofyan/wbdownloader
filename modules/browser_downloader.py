"""
Browser-based downloader using Playwright for better bot detection avoidance
"""

import asyncio
import random
import time
from pathlib import Path
from urllib.parse import urlparse, unquote
import mimetypes
import aiofiles
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from playwright_stealth import Stealth
from tqdm.asyncio import tqdm

from .wayback_api import WaybackAPI


class BrowserDownloader:
    """Handle downloads using a real browser engine (Playwright)"""
    
    def __init__(self, output_dir, logger=None, headless=False, proxy=None):
        self.output_dir = Path(output_dir)
        self.logger = logger
        self.headless = headless
        self.proxy = proxy
        self.wayback_api = WaybackAPI()
        
        # Browser instances
        self.playwright = None
        self.browser = None
        self.context = None
        
        # Statistics
        self.downloaded = 0
        self.failed = 0
        self.skipped = 0
        
        # Request tracking
        self.last_request_time = 0
        self.request_count = 0
    
    async def __aenter__(self):
        """Initialize browser and context"""
        self.playwright = await async_playwright().start()
        
        # Browser launch options
        launch_options = {
            'headless': self.headless,
            'args': [
                '--disable-blink-features=AutomationControlled',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-site-isolation-trials',
                '--disable-web-security',
                '--disable-features=BlockInsecurePrivateNetworkRequests',
            ]
        }
        
        # Add proxy if provided
        if self.proxy:
            proxy_parts = urlparse(self.proxy)
            proxy_config = {
                'server': f"{proxy_parts.scheme}://{proxy_parts.hostname}:{proxy_parts.port}"
            }
            if proxy_parts.username:
                proxy_config['username'] = proxy_parts.username
                proxy_config['password'] = proxy_parts.password or ''
            launch_options['proxy'] = proxy_config
            
            if self.logger:
                self.logger.info(f"Using proxy: {self.proxy}")
        
        # Launch browser
        self.browser = await self.playwright.chromium.launch(**launch_options)
        
        # Create context with browser-like settings
        viewport_sizes = [
            {'width': 1920, 'height': 1080},
            {'width': 1366, 'height': 768},
            {'width': 1440, 'height': 900},
            {'width': 1536, 'height': 864}
        ]
        viewport = random.choice(viewport_sizes)
        
        context_options = {
            'viewport': viewport,
            'user_agent': self._get_random_user_agent(),
            'locale': 'en-US',
            'timezone_id': 'America/New_York',
            'permissions': ['geolocation'],
            'geolocation': {'latitude': 40.7128, 'longitude': -74.0060},  # New York
            'color_scheme': 'light',
            'extra_http_headers': {
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'DNT': '1',
            }
        }
        
        self.context = await self.browser.new_context(**context_options)
        
        # Apply stealth to context
        await Stealth().apply_stealth_async(self.context)
        
        # Set cookies to appear more legitimate
        await self.context.add_cookies([
            {
                'name': 'session_id',
                'value': f"session_{random.randint(1000000, 9999999)}",
                'domain': '.archive.org',
                'path': '/'
            }
        ])
        
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up browser resources"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    def _get_random_user_agent(self):
        """Get a random realistic user agent"""
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        ]
        return random.choice(user_agents)
    
    async def _apply_human_delay(self):
        """Apply human-like delay between actions"""
        current_time = time.time()
        self.request_count += 1
        
        # Base delay range (1 to 3 seconds for browser)
        min_delay = 1.0
        max_delay = 3.0
        
        # Every 5 requests, add a longer pause
        if self.request_count % 5 == 0:
            min_delay = 3.0
            max_delay = 7.0
            if self.logger:
                self.logger.debug(f"Applied longer pause after {self.request_count} requests")
        
        # Calculate time since last request
        time_since_last = current_time - self.last_request_time
        
        # Generate random delay with some variance
        target_delay = random.uniform(min_delay, max_delay)
        
        # Add small random micro-pauses to simulate thinking
        if random.random() < 0.3:
            target_delay += random.uniform(0.5, 1.5)
        
        # Only sleep if we haven't waited long enough
        if time_since_last < target_delay:
            sleep_time = target_delay - time_since_last
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def _simulate_human_behavior(self, page: Page):
        """Simulate human-like behavior on the page"""
        try:
            # Random mouse movements
            for _ in range(random.randint(2, 4)):
                x = random.randint(100, 800)
                y = random.randint(100, 600)
                await page.mouse.move(x, y)
                await asyncio.sleep(random.uniform(0.1, 0.3))
            
            # Random scrolling
            scroll_attempts = random.randint(1, 3)
            for _ in range(scroll_attempts):
                scroll_amount = random.randint(100, 500)
                await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
                await asyncio.sleep(random.uniform(0.5, 1.5))
            
            # Scroll back to top
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(random.uniform(0.3, 0.7))
            
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Error simulating human behavior: {str(e)}")
    
    async def download_page(self, wayback_url, original_url, is_main=False):
        """
        Download a page using browser
        
        Args:
            wayback_url: Wayback Machine URL
            original_url: Original URL for determining file path
            is_main: Whether this is the main HTML file
            
        Returns:
            Tuple of (content, file_path) or (None, None) on failure
        """
        page = None
        try:
            # Apply human-like delay
            await self._apply_human_delay()
            
            # Check if file already exists
            file_path = self._determine_file_path(original_url, is_main)
            if file_path.exists():
                self.skipped += 1
                if self.logger:
                    self.logger.debug(f"File already exists, skipping: {file_path}")
                
                # Read existing file
                content = await self._read_existing_file(file_path)
                if content is not None:
                    return content, file_path
            
            # Create new page with timeout
            page = await self.context.new_page()
            
            # Set extra headers for this specific request
            await page.set_extra_http_headers({
                'Referer': 'https://web.archive.org/' if not is_main else 'https://google.com/',
                'Cache-Control': 'no-cache',
            })
            
            # Navigate with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    # Go to page with extended timeout
                    response = await page.goto(
                        wayback_url, 
                        wait_until='domcontentloaded',
                        timeout=60000  # 60 seconds timeout
                    )
                    
                    if response and response.status == 200:
                        break
                    elif response and response.status == 429:
                        # Rate limited
                        if attempt < max_retries - 1:
                            wait_time = (attempt + 1) * 5 + random.uniform(0, 5)
                            if self.logger:
                                self.logger.warning(f"Rate limited (429), waiting {wait_time:.1f}s")
                            await asyncio.sleep(wait_time)
                            continue
                    else:
                        if self.logger:
                            self.logger.warning(f"Unexpected status: {response.status if response else 'No response'}")
                        
                except Exception as e:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 3 + random.uniform(0, 3)
                        if self.logger:
                            self.logger.warning(f"Navigation error, retrying in {wait_time:.1f}s: {str(e)}")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        raise
            
            # Wait for content to load
            await page.wait_for_load_state('networkidle', timeout=30000)
            
            # Simulate human behavior
            await self._simulate_human_behavior(page)
            
            # Get page content
            content = await page.content()
            
            # Create directory
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save content
            async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
                await f.write(content)
            
            self.downloaded += 1
            if self.logger:
                self.logger.debug(f"Downloaded via browser: {file_path}")
            
            return content, file_path
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Browser download failed for {wayback_url}: {str(e)}")
            self.failed += 1
            return None, None
        
        finally:
            if page:
                await page.close()
    
    async def download_asset(self, wayback_url, original_url):
        """
        Download an asset (image, CSS, JS, etc.) using browser's network
        
        Args:
            wayback_url: Wayback Machine URL of the asset
            original_url: Original URL for determining file path
            
        Returns:
            Tuple of (success, file_path) or (False, None) on failure
        """
        page = None
        try:
            # Apply delay
            await self._apply_human_delay()
            
            # Determine file path
            file_path = self._determine_file_path(original_url, is_main=False)
            
            # Check if already exists
            if file_path.exists():
                self.skipped += 1
                return True, file_path
            
            # Create page for download
            page = await self.context.new_page()
            
            # Use page's request context to download
            response = await page.request.get(wayback_url)
            
            if response.status == 200:
                content = await response.body()
                
                # Create directory
                file_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Save file
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(content)
                
                self.downloaded += 1
                if self.logger:
                    self.logger.debug(f"Downloaded asset: {file_path}")
                
                return True, file_path
            else:
                if self.logger:
                    self.logger.warning(f"Failed to download asset {wayback_url}: {response.status}")
                self.failed += 1
                return False, None
                
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error downloading asset {wayback_url}: {str(e)}")
            self.failed += 1
            return False, None
        
        finally:
            if page:
                await page.close()
    
    async def download_assets_batch(self, assets):
        """
        Download multiple assets with progress bar
        
        Args:
            assets: List of asset dictionaries
        """
        # Filter out None assets
        valid_assets = [a for a in assets if a is not None]
        
        # Create progress bar
        progress_bar = tqdm(
            total=len(valid_assets),
            desc="Downloading assets",
            unit="files"
        )
        
        # Download assets sequentially (browser mode is already slower)
        for asset in valid_assets:
            try:
                await self.download_asset(
                    asset['wayback_url'],
                    asset['original_url']
                )
            except Exception as e:
                if self.logger:
                    self.logger.debug(f"Failed to download {asset['wayback_url']}: {str(e)}")
            finally:
                progress_bar.update(1)
        
        progress_bar.close()
        
        # Log statistics
        if self.logger:
            self.logger.info(f"Browser download statistics:")
            self.logger.info(f"  Downloaded: {self.downloaded}")
            self.logger.info(f"  Failed: {self.failed}")
            self.logger.info(f"  Skipped: {self.skipped}")
    
    def _determine_file_path(self, url, is_main):
        """
        Determine local file path for URL
        
        Args:
            url: Original URL
            is_main: Whether this is the main file
            
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
            # Default to .html for pages without extension
            path += '.html'
        
        # Construct full path
        full_path = self.output_dir / path
        
        return full_path
    
    async def _read_existing_file(self, file_path):
        """Read existing file content"""
        try:
            # Try to read as text first
            try:
                async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                    return await f.read()
            except UnicodeDecodeError:
                # Read as binary if text fails
                async with aiofiles.open(file_path, 'rb') as f:
                    return await f.read()
        except Exception as e:
            if self.logger:
                self.logger.debug(f"Failed to read existing file {file_path}: {str(e)}")
            return None