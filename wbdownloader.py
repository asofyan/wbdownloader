#!/usr/bin/env python3
"""
Wayback Machine Downloader
A CLI tool to download websites from the Internet Archive's Wayback Machine
"""

import argparse
import asyncio
import sys
from pathlib import Path
from urllib.parse import urlparse
from collections import deque

from modules.wayback_api import WaybackAPI
from modules.parser import AssetParser
from modules.downloader import AsyncDownloader
from modules.browser_downloader import BrowserDownloader
from modules.utils import setup_logging, validate_timestamp, should_download_url, validate_proxy_url


async def download_with_http(downloader, wayback_api, parser, args, logger):
    """Handle downloads using HTTP mode (original implementation)"""
    downloaded_urls = set()
    pages_queue = deque()
    
    # Construct initial Wayback URL
    initial_wayback_url = wayback_api.construct_url(args.url, args.snapshot)
    logger.info(f"Starting download from: {initial_wayback_url}")
    
    # Add initial URL to queue
    pages_queue.append({
        'wayback_url': initial_wayback_url,
        'original_url': args.url,
        'level': 1
    })
    
    # Process pages level by level
    current_level = 1
    
    while pages_queue and current_level <= args.level:
        # Get all pages at current level
        pages_at_level = []
        while pages_queue and pages_queue[0]['level'] == current_level:
            pages_at_level.append(pages_queue.popleft())
        
        if pages_at_level:
            logger.info(f"\n=== Processing Level {current_level} ===")
            logger.info(f"Pages to download: {len(pages_at_level)}")
        
        # Download all pages at current level
        for page_info in pages_at_level:
            wayback_url = page_info['wayback_url']
            original_url = page_info['original_url']
            
            # Skip if already processed
            if wayback_url in downloaded_urls:
                logger.debug(f"Skipping already processed: {original_url}")
                continue
            
            logger.info(f"Processing: {original_url}")
            
            # Download the page (this will check for existing files automatically)
            page_content, page_path = await downloader.download_file(
                wayback_url,
                original_url,
                is_main=(current_level == 1 and page_info == pages_at_level[0])
            )
            
            if not page_content:
                logger.warning(f"Failed to get content for: {original_url}")
                continue
            
            # Mark as processed
            downloaded_urls.add(wayback_url)
            
            # Extract and download assets from this page immediately (unless --no-assets flag is set)
            if not args.no_assets:
                logger.debug(f"Parsing and downloading assets from: {original_url}")
                page_assets = parser.extract_assets(page_content, wayback_url)
                
                # Parse CSS files for additional assets
                css_assets = [asset for asset in page_assets if asset and asset['type'] == 'css']
                for css_asset in css_assets:
                    css_url = css_asset['wayback_url']
                    logger.debug(f"Downloading CSS for parsing: {css_url}")
                    css_content, _ = await downloader.download_file(
                        css_url,
                        css_asset['original_url'],
                        save=False
                    )
                    if css_content:
                        css_embedded_assets = parser.extract_css_assets(css_content, css_url)
                        page_assets.extend(css_embedded_assets)
                
                # Remove duplicates for this page
                unique_page_assets = []
                seen_asset_urls = set()
                for asset in page_assets:
                    if asset and asset['wayback_url'] not in seen_asset_urls:
                        seen_asset_urls.add(asset['wayback_url'])
                        unique_page_assets.append(asset)
                
                if unique_page_assets:
                    logger.info(f"Downloading {len(unique_page_assets)} assets from this page...")
                    await downloader.download_assets(unique_page_assets, sequential=args.sequential_assets)
            
            # Extract links for next level (if not at max level)
            if current_level < args.level:
                logger.debug(f"Extracting links from: {original_url}")
                links = parser.extract_links(page_content, wayback_url)
                
                # Filter links
                for link in links:
                    link_original_url = link['original_url']
                    link_wayback_url = link['wayback_url']
                    
                    # Check if we should download this link
                    if should_download_url(link_original_url, args.url, downloaded_urls):
                        # Check if wayback URL is already queued or processed
                        if link_wayback_url not in downloaded_urls:
                            pages_queue.append({
                                'wayback_url': link_wayback_url,
                                'original_url': link_original_url,
                                'level': current_level + 1
                            })
                
                logger.debug(f"Found {len(links)} links, queued {len([l for l in links if should_download_url(l['original_url'], args.url, downloaded_urls)])} for download")
        
        # Move to next level
        current_level += 1
    
    logger.info(f"\n=== Download Summary ===")
    logger.info(f"Processed {len(downloaded_urls)} pages")
    logger.info(f"Downloaded: {downloader.downloaded}, Skipped: {downloader.skipped}, Failed: {downloader.failed}")


async def download_with_browser(downloader, wayback_api, parser, args, logger):
    """Handle downloads using browser mode"""
    downloaded_urls = set()
    pages_queue = deque()
    
    # Construct initial Wayback URL
    initial_wayback_url = wayback_api.construct_url(args.url, args.snapshot)
    logger.info(f"Starting browser download from: {initial_wayback_url}")
    
    # Add initial URL to queue
    pages_queue.append({
        'wayback_url': initial_wayback_url,
        'original_url': args.url,
        'level': 1
    })
    
    # Process pages level by level
    current_level = 1
    
    while pages_queue and current_level <= args.level:
        # Get all pages at current level
        pages_at_level = []
        while pages_queue and pages_queue[0]['level'] == current_level:
            pages_at_level.append(pages_queue.popleft())
        
        if pages_at_level:
            logger.info(f"\n=== Processing Level {current_level} ===")
            logger.info(f"Pages to download: {len(pages_at_level)}")
        
        # Download all pages at current level
        for page_info in pages_at_level:
            wayback_url = page_info['wayback_url']
            original_url = page_info['original_url']
            
            # Skip if already processed
            if wayback_url in downloaded_urls:
                logger.debug(f"Skipping already processed: {original_url}")
                continue
            
            logger.info(f"Processing with browser: {original_url}")
            
            # Download the page using browser
            page_content, page_path = await downloader.download_page(
                wayback_url,
                original_url,
                is_main=(current_level == 1 and page_info == pages_at_level[0])
            )
            
            if not page_content:
                logger.warning(f"Failed to get content for: {original_url}")
                continue
            
            # Mark as processed
            downloaded_urls.add(wayback_url)
            
            # Extract and download assets from this page (unless --no-assets flag is set)
            if not args.no_assets:
                logger.debug(f"Parsing assets from: {original_url}")
                page_assets = parser.extract_assets(page_content, wayback_url)
                
                # Parse CSS files for additional assets
                css_assets = [asset for asset in page_assets if asset and asset['type'] == 'css']
                for css_asset in css_assets:
                    css_url = css_asset['wayback_url']
                    logger.debug(f"Downloading CSS for parsing: {css_url}")
                    success, _ = await downloader.download_asset(
                        css_url,
                        css_asset['original_url']
                    )
                    if success:
                        # Read CSS content for parsing
                        css_path = downloader._determine_file_path(css_asset['original_url'], False)
                        if css_path.exists():
                            try:
                                with open(css_path, 'r', encoding='utf-8') as f:
                                    css_content = f.read()
                                css_embedded_assets = parser.extract_css_assets(css_content, css_url)
                                page_assets.extend(css_embedded_assets)
                            except:
                                pass
                
                # Remove duplicates
                unique_page_assets = []
                seen_asset_urls = set()
                for asset in page_assets:
                    if asset and asset['wayback_url'] not in seen_asset_urls:
                        seen_asset_urls.add(asset['wayback_url'])
                        unique_page_assets.append(asset)
                
                if unique_page_assets:
                    logger.info(f"Downloading {len(unique_page_assets)} assets from this page...")
                    await downloader.download_assets_batch(unique_page_assets)
            
            # Extract links for next level (if not at max level)
            if current_level < args.level:
                logger.debug(f"Extracting links from: {original_url}")
                links = parser.extract_links(page_content, wayback_url)
                
                # Filter links
                for link in links:
                    link_original_url = link['original_url']
                    link_wayback_url = link['wayback_url']
                    
                    # Check if we should download this link
                    if should_download_url(link_original_url, args.url, downloaded_urls):
                        # Check if wayback URL is already queued or processed
                        if link_wayback_url not in downloaded_urls:
                            pages_queue.append({
                                'wayback_url': link_wayback_url,
                                'original_url': link_original_url,
                                'level': current_level + 1
                            })
                
                logger.debug(f"Found {len(links)} links, queued {len([l for l in links if should_download_url(l['original_url'], args.url, downloaded_urls)])} for download")
        
        # Move to next level
        current_level += 1
    
    logger.info(f"\n=== Browser Download Summary ===")
    logger.info(f"Processed {len(downloaded_urls)} pages")
    logger.info(f"Downloaded: {downloader.downloaded}, Skipped: {downloader.skipped}, Failed: {downloader.failed}")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description='Download websites from the Wayback Machine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  wbdownloader -f http://example.com -s 20240417160532
  wbdownloader -f http://example.com -s 20240417160532 -o ./output
  wbdownloader -f http://example.com -s 20240417160532 -c 10
  wbdownloader -f http://example.com -s 20240417160532 -l 2
  wbdownloader -f http://example.com -s 20240417160532 -p http://proxy.example.com:8080
        '''
    )
    
    parser.add_argument(
        '-f', '--url',
        required=True,
        help='URL to download from Wayback Machine'
    )
    
    parser.add_argument(
        '-s', '--snapshot',
        required=True,
        help='Snapshot timestamp (YYYYMMDDHHMMSS format)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output directory (defaults to domain name)'
    )
    
    parser.add_argument(
        '-c', '--concurrent',
        type=int,
        default=1,
        help='Number of concurrent downloads (default: 1, single process to avoid bot detection)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    parser.add_argument(
        '--no-assets',
        action='store_true',
        help='Download only HTML without assets'
    )
    
    parser.add_argument(
        '-l', '--level',
        type=int,
        default=1,
        help='Depth of links to follow (default: 1, main page only)'
    )
    
    parser.add_argument(
        '-p', '--proxy',
        help='Proxy URL (e.g., http://proxy.example.com:8080 or http://user:pass@proxy.example.com:8080)'
    )
    
    parser.add_argument(
        '--sequential-assets',
        action='store_true',
        help='Download assets sequentially instead of concurrently (slower but less detectable)'
    )
    
    parser.add_argument(
        '--browser',
        action='store_true',
        help='Use browser engine (Playwright) for downloads - better for sites with bot detection'
    )
    
    parser.add_argument(
        '--headless',
        action='store_true',
        help='Run browser in headless mode (faster but more detectable, only with --browser)'
    )
    
    return parser.parse_args()


async def main():
    args = parse_arguments()
    
    # Setup logging
    logger = setup_logging(args.verbose)
    
    # Validate timestamp format
    if not validate_timestamp(args.snapshot):
        logger.error(f"Invalid timestamp format: {args.snapshot}")
        logger.error("Expected format: YYYYMMDDHHMMSS")
        sys.exit(1)
    
    # Validate proxy URL format
    if not validate_proxy_url(args.proxy):
        logger.error(f"Invalid proxy URL format: {args.proxy}")
        logger.error("Expected format: http://proxy.example.com:8080 or http://user:pass@proxy.example.com:8080")
        sys.exit(1)
    
    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        parsed_url = urlparse(args.url)
        domain = parsed_url.netloc or parsed_url.path.split('/')[0]
        output_dir = Path(domain)
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {output_dir}")
    
    # Initialize components
    wayback_api = WaybackAPI()
    parser = AssetParser()
    
    try:
        if args.browser:
            # Browser mode
            logger.info("Using browser mode (Playwright) for downloads")
            if args.headless:
                logger.info("Running in headless mode")
            else:
                logger.info("Running in headful mode (visible browser)")
            
            # Use browser downloader
            async with BrowserDownloader(
                output_dir=output_dir,
                logger=logger,
                headless=args.headless,
                proxy=args.proxy
            ) as downloader:
                await download_with_browser(downloader, wayback_api, parser, args, logger)
        else:
            # HTTP mode (original implementation)
            logger.info("Using HTTP mode for downloads")
            
            async with AsyncDownloader(
                output_dir=output_dir,
                max_concurrent=args.concurrent,
                logger=logger,
                proxy=args.proxy
            ) as downloader:
                await download_with_http(downloader, wayback_api, parser, args, logger)
                
            logger.info(f"Files saved to: {output_dir}")
        
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        if args.verbose:
            logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())