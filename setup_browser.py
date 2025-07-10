#!/usr/bin/env python3
"""
Setup script for Playwright browser installation
"""

import subprocess
import sys
import os

def install_playwright_browsers():
    """Install Playwright browsers"""
    print("Installing Playwright browsers...")
    
    try:
        # Install Playwright browsers
        result = subprocess.run([
            sys.executable, '-m', 'playwright', 'install', 'chromium'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Playwright Chromium browser installed successfully")
            print("\nYou can now use the --browser flag to enable browser mode:")
            print("  wbdownloader -f http://example.com -s 20240417160532 --browser")
            print("\nFor headless mode (faster but more detectable):")
            print("  wbdownloader -f http://example.com -s 20240417160532 --browser --headless")
            return True
        else:
            print("✗ Failed to install Playwright browsers")
            print(f"Error: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"✗ Error installing Playwright browsers: {str(e)}")
        return False

def check_dependencies():
    """Check if required dependencies are installed"""
    print("Checking dependencies...")
    
    try:
        import playwright
        print("✓ Playwright is installed")
        
        try:
            from playwright_stealth import stealth_async
            print("✓ playwright-stealth is installed")
        except ImportError:
            print("✗ playwright-stealth is not installed")
            print("Please install it with: pip install playwright-stealth")
            return False
            
        return True
    except ImportError:
        print("✗ Playwright is not installed")
        print("Please install it with: pip install playwright")
        return False

def main():
    """Main setup function"""
    print("WB Downloader Browser Mode Setup")
    print("=" * 40)
    
    # Check dependencies
    if not check_dependencies():
        print("\nPlease install the required dependencies first:")
        print("  pip install -r requirements.txt")
        sys.exit(1)
    
    # Install browsers
    if install_playwright_browsers():
        print("\n✓ Browser mode setup completed successfully!")
        print("\nBrowser mode features:")
        print("- Real browser engine (less detectable)")
        print("- Handles JavaScript and dynamic content")
        print("- Better success rate against bot detection")
        print("- Slower than HTTP mode but more reliable")
    else:
        print("\n✗ Browser mode setup failed")
        sys.exit(1)

if __name__ == '__main__':
    main()