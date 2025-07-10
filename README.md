# Wayback Machine Downloader

A Python CLI tool to download websites from the Internet Archive's Wayback Machine, preserving the complete structure including all assets.

## Features

- Download complete websites from specific Wayback Machine snapshots
- Multi-level crawling: follow links to download entire site sections
- Preserve original directory structure
- Download all assets: HTML, CSS, JavaScript, images, fonts, etc.
- **Two download modes**: HTTP client (fast) and Browser mode (more reliable)
- **Browser mode**: Uses Playwright for better bot detection avoidance
- Concurrent downloads for faster performance
- Progress tracking with visual progress bars
- Handles complex Wayback Machine URLs
- Extracts embedded assets from CSS files
- Same-domain filtering to avoid downloading external sites
- Intelligent retry logic with exponential backoff for rate limiting
- Page-by-page asset downloading to reduce memory usage and server load
- Resume capability - skips already downloaded files
- Proxy support for bypassing IP restrictions and rate limits
- **Anti-bot detection**: Random delays, realistic headers, human-like behavior simulation

## Installation

1. Clone or download this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. **For browser mode** (recommended for sites with bot detection):

```bash
python setup_browser.py
```

This will install Playwright browsers needed for browser mode.

## Usage

Basic usage:
```bash
python wbdownloader.py -f http://example.com -s 20240417160532
```

### Command Line Options

- `-f, --url` (required): URL to download from Wayback Machine
- `-s, --snapshot` (required): Snapshot timestamp in YYYYMMDDHHMMSS format
- `-o, --output`: Output directory (defaults to domain name)
- `-c, --concurrent`: Number of concurrent downloads (default: 1)
- `-l, --level`: Depth of links to follow (default: 1, main page only)
- `-p, --proxy`: Proxy URL for downloads (e.g., http://proxy.example.com:8080)
- `-v, --verbose`: Enable verbose logging
- `--no-assets`: Download only HTML without assets
- `--sequential-assets`: Download assets sequentially (slower but less detectable)
- `--browser`: Use browser mode for better bot detection avoidance
- `--headless`: Run browser in headless mode (only with --browser)

### Examples

Download a website with specific snapshot:
```bash
python wbdownloader.py -f http://example.com -s 20240417160532
```

Specify output directory:
```bash
python wbdownloader.py -f http://example.com -s 20240417160532 -o ./downloads/example
```

Increase concurrent downloads for faster speed:
```bash
python wbdownloader.py -f http://example.com -s 20240417160532 -c 10
```

Download only HTML without assets:
```bash
python wbdownloader.py -f http://example.com -s 20240417160532 --no-assets
```

Enable verbose logging:
```bash
python wbdownloader.py -f http://example.com -s 20240417160532 -v
```

Download multiple levels (follow links):
```bash
# Download main page + all linked pages (2 levels)
python wbdownloader.py -f http://example.com -s 20240417160532 -l 2

# Download up to 3 levels deep
python wbdownloader.py -f http://example.com -s 20240417160532 -l 3
```

Use proxy for downloads:
```bash
# Basic proxy
python wbdownloader.py -f http://example.com -s 20240417160532 -p http://proxy.example.com:8080

# Authenticated proxy
python wbdownloader.py -f http://example.com -s 20240417160532 -p http://user:pass@proxy.example.com:8080

# Proxy with multi-level download
python wbdownloader.py -f http://example.com -s 20240417160532 -l 2 -p http://proxy.example.com:8080
```

Use browser mode for better bot detection avoidance:
```bash
# Browser mode (recommended for sites with bot detection)
python wbdownloader.py -f http://example.com -s 20240417160532 --browser

# Browser mode with headless option (faster but more detectable)
python wbdownloader.py -f http://example.com -s 20240417160532 --browser --headless

# Browser mode with sequential assets (slowest but most reliable)
python wbdownloader.py -f http://example.com -s 20240417160532 --browser --sequential-assets

# Browser mode with proxy
python wbdownloader.py -f http://example.com -s 20240417160532 --browser -p http://proxy.example.com:8080
```

## Output Structure

The tool preserves the original website structure. For example:
```
example.com/
├── index.html
├── css/
│   ├── style.css
│   └── bootstrap.min.css
├── js/
│   ├── main.js
│   └── jquery.min.js
├── images/
│   ├── logo.png
│   └── banner.jpg
└── fonts/
    └── roboto.woff2
```

## How It Works

1. **Main Page Download**: Downloads the main HTML page from the specified Wayback Machine snapshot
2. **Link Following**: If level > 1, extracts all hyperlinks from downloaded pages
3. **Level-by-Level Processing**: Downloads pages level by level using breadth-first search
4. **Same-Domain Filtering**: Only follows links within the same domain to avoid external sites
5. **Asset Extraction**: Parses HTML to find all referenced assets (CSS, JS, images, etc.)
6. **CSS Parsing**: Analyzes CSS files to find additional assets (background images, fonts, etc.)
7. **Concurrent Downloads**: Downloads all assets concurrently for efficiency
8. **Structure Preservation**: Saves files maintaining the original URL path structure

## Proxy Configuration

The tool supports HTTP and HTTPS proxies for bypassing IP restrictions or rate limits:

### Proxy URL Format
- Basic proxy: `http://proxy.example.com:8080`
- Authenticated proxy: `http://username:password@proxy.example.com:8080`
- HTTPS proxy: `https://proxy.example.com:8080`

### Common Use Cases
- **IP Blacklisting**: If your IP has been blacklisted by the Wayback Machine
- **Rate Limiting**: Distribute requests across multiple IP addresses
- **Geographic Restrictions**: Access content through different geographical locations
- **Corporate Networks**: Route traffic through corporate proxy servers

### Proxy Sources
- Free proxy lists (less reliable)
- Paid proxy services (more reliable)
- Corporate proxy servers
- VPN services that provide HTTP proxies

## Requirements

- Python 3.7+
- Dependencies listed in requirements.txt

## Download Modes

### HTTP Mode (Default)
- **Fast**: Uses HTTP client for downloads
- **Lightweight**: Lower resource usage
- **Good for**: Simple sites without bot detection
- **Limitations**: May be detected as a bot on some sites

### Browser Mode (Recommended for problematic sites)
- **Reliable**: Uses real browser engine (Playwright)
- **Stealth**: Advanced bot detection avoidance
- **JavaScript**: Handles dynamic content and JavaScript
- **Realistic**: Simulates human browsing behavior
- **Limitations**: Slower and uses more resources

### When to Use Browser Mode
- When HTTP mode gets "Connection closed" errors
- Sites with aggressive bot detection
- Sites that require JavaScript to load content
- When you need maximum reliability

## Limitations

- Respects Wayback Machine rate limits
- Browser mode is slower but more reliable
- Some dynamic content loaded by JavaScript may not be captured (HTTP mode)
- Very large websites may take considerable time to download

## Changelog

### Version 2.0.0 - Bot Detection Avoidance Update

#### **Major Features Added**

**Browser Mode Implementation**
- ✅ Added Playwright-based browser downloader for better bot detection avoidance
- ✅ Implemented playwright-stealth for advanced anti-detection capabilities
- ✅ Added `--browser` flag to enable browser mode
- ✅ Added `--headless` flag for headless browser operation

**Anti-Bot Detection Features**
- ✅ Realistic User-Agent rotation from 6 popular browsers
- ✅ Browser-like headers (Accept, Accept-Language, Accept-Encoding, DNT, Sec-Fetch, etc.)
- ✅ Human-like behavior simulation (mouse movements, scrolling, random pauses)
- ✅ Smart delay system (1-3 seconds between requests, longer pauses every 5 requests)
- ✅ Cookie jar and session persistence
- ✅ Connection pooling with realistic limits

**Performance & Safety Improvements**
- ✅ Changed default concurrent downloads from 3 to 1 (reduces bot detection)
- ✅ Added `--sequential-assets` flag for maximum stealth mode
- ✅ Improved retry logic with exponential backoff and jitter
- ✅ Extended timeouts (60 seconds total, 30 seconds connect)
- ✅ Enhanced error handling for connection issues

#### 🔧 **Technical Improvements**

**HTTP Mode Enhancements**
- ✅ Better User-Agent rotation with realistic browser strings
- ✅ Improved request delays (0.5-2 seconds, up to 5 seconds every 10 requests)
- ✅ Enhanced retry mechanism (increased from 3 to 5 retries)
- ✅ More realistic headers and connection settings

**Code Structure**
- ✅ Created separate `BrowserDownloader` class for browser-based downloads
- ✅ Extracted HTTP download logic into `download_with_http()` function
- ✅ Added `setup_browser.py` script for easy Playwright installation
- ✅ Modular design allowing both HTTP and browser modes

#### 📦 **New Dependencies**
- ✅ Added `playwright>=1.40.0` for browser automation
- ✅ Added `playwright-stealth>=1.0.6` for bot detection avoidance

#### 🚀 **Usage Examples**

**For sites with bot detection (recommended):**
```bash
python wbdownloader.py -f https://example.com -s 20240417160532 --browser
```

**Maximum stealth mode:**
```bash
python wbdownloader.py -f https://example.com -s 20240417160532 --browser --sequential-assets
```

**With proxy support:**
```bash
python wbdownloader.py -f https://example.com -s 20240417160532 --browser -p http://proxy.example.com:8080
```

#### 🛠️ **Setup Instructions**

1. Install new dependencies:
```bash
pip install -r requirements.txt
```

2. Setup browser mode (one-time):
```bash
python setup_browser.py
```

#### 🎯 **Problem Solved**

This update specifically addresses the "Connection closed" error that occurs when the Wayback Machine detects and blocks bot traffic. The new browser mode uses a real Chrome browser engine that's much harder to detect, providing:

- **Higher success rate** for problematic sites
- **Better reliability** against bot detection systems
- **JavaScript support** for dynamic content
- **Human-like behavior** that mimics real user interactions

#### 📊 **Performance Comparison**

| Mode | Speed | Detection Risk | Resource Usage | Recommended For |
|------|-------|----------------|----------------|-----------------|
| HTTP | Fast | High | Low | Simple sites |
| Browser | Slow | Low | High | Sites with bot detection |
| Browser + Sequential | Slowest | Very Low | High | Maximum stealth |

---

## License

This tool is for educational and archival purposes. Please respect website copyrights and terms of service when using downloaded content.