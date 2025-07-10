# Wayback Machine Downloader

A Python CLI tool to download websites from the Internet Archive's Wayback Machine, preserving the complete structure including all assets.

## Features

- Download complete websites from specific Wayback Machine snapshots
- Multi-level crawling: follow links to download entire site sections
- Preserve original directory structure
- Download all assets: HTML, CSS, JavaScript, images, fonts, etc.
- Concurrent downloads for faster performance
- Progress tracking with visual progress bars
- Handles complex Wayback Machine URLs
- Extracts embedded assets from CSS files
- Same-domain filtering to avoid downloading external sites
- Intelligent retry logic with exponential backoff for rate limiting
- Page-by-page asset downloading to reduce memory usage and server load
- Resume capability - skips already downloaded files
- Proxy support for bypassing IP restrictions and rate limits

## Installation

1. Clone or download this repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

Basic usage:
```bash
python wbdownloader.py -f http://example.com -s 20240417160532
```

### Command Line Options

- `-f, --url` (required): URL to download from Wayback Machine
- `-s, --snapshot` (required): Snapshot timestamp in YYYYMMDDHHMMSS format
- `-o, --output`: Output directory (defaults to domain name)
- `-c, --concurrent`: Number of concurrent downloads (default: 3)
- `-l, --level`: Depth of links to follow (default: 1, main page only)
- `-p, --proxy`: Proxy URL for downloads (e.g., http://proxy.example.com:8080)
- `-v, --verbose`: Enable verbose logging
- `--no-assets`: Download only HTML without assets

### Examples

Download a website with specific snapshot:
```bash
python wbdownloader.py -f http://akademiberbagi.org -s 20240417160532
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

## Limitations

- Respects Wayback Machine rate limits
- Some dynamic content loaded by JavaScript may not be captured
- Very large websites may take considerable time to download

## License

This tool is for educational and archival purposes. Please respect website copyrights and terms of service when using downloaded content.