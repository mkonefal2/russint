"""
Facebook Scraper - Single Post
Scrapes a single Facebook post given its URL.
Saves JSON + Screenshot.

Requires Chrome running with:
  chrome.exe --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome-debug"
"""

import json
import sys
import re
from datetime import datetime
from pathlib import Path
import asyncio
from playwright.async_api import async_playwright

async def scrape_single_post(target_url):
    base_dir = Path(__file__).parent.parent.parent
    
    print("="*60)
    print("FACEBOOK SCRAPER - SINGLE POST")
    print("="*60)
    print(f"Target: {target_url}")
    
    try:
        async with async_playwright() as p:
            print("\n[*] Launching Chrome...")
            # Launch browser instead of connecting
            browser = await p.chromium.launch(
                headless=False,
                channel='chrome', # Try to use installed Chrome
                args=['--start-maximized']
            )
            
            # Create context with specific viewport
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                locale='pl-PL'
            )
            
            page = await context.new_page()
            
            print(f"[*] Navigating to: {target_url}")
            await page.goto(target_url)
            
            print("\n" + "="*50)
            print("ACTION REQUIRED:")
            print("1. Browser is open.")
            print("2. Log in to Facebook if needed.")
            print("3. Ensure the post is visible.")
            print("4. Press ENTER in this terminal to start scraping.")
            print("="*50 + "\n")
            
            input(">>> Press ENTER when ready to scrape... ")
            
            print("[*] Starting scrape...")
            
            # Extract handle from URL
            handle_match = re.search(r'facebook\.com/([^/?]+)', target_url)
            handle = handle_match.group(1) if handle_match else "unknown"
            if handle == "permalink.php":
                # Try to find handle in page title or content if it's a permalink.php URL
                handle = "unknown_profile" 
            
            print(f"[*] Handle: {handle}")
            
            # Directories
            posts_dir = base_dir / "data" / "raw" / "facebook" / handle
            screenshots_dir = base_dir / "data" / "evidence" / "facebook" / handle
            posts_dir.mkdir(parents=True, exist_ok=True)
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            
            # Find the post container
            # On a single post page, the main post usually has role="article" or aria-posinset
            # We try to find the most prominent article
            
            print("[*] Looking for post container...")
            
            # Strategy 1: div[role="main"] - captures post + comments (safer for "whole post" view)
            container = await page.query_selector('div[role="main"]')
            
            if not container:
                print("[!] Could not find div[role='main'], trying div[role='article']...")
                container = await page.query_selector('div[role="article"]')
            
            if not container:
                print("[!] Could not find main container. Taking full page screenshot.")
                container = page # Fallback to page for screenshot
            
            # Extract text
            try:
                if container != page:
                    full_text = await container.inner_text()
                else:
                    full_text = await page.inner_text('body')
            except:
                full_text = ""
                
            clean_text = full_text.replace('Facebook', '').replace('\n', ' ').strip()
            
            # Generate ID
            # Try to extract pfbid from URL
            pfbid_match = re.search(r'pfbid([0-9a-zA-Z]+)', target_url)
            if pfbid_match:
                unique_id = f"pfbid{pfbid_match.group(1)}"
            else:
                # Try story_fbid
                story_match = re.search(r'story_fbid=(\d+)', target_url)
                if story_match:
                    unique_id = story_match.group(1)
                else:
                    # Hash fallback
                    unique_id = f"h{hash(clean_text[:200]) & 0xFFFFFFFF:08x}"
            
            post_id = f"fb_{handle}_{unique_id}"
            print(f"[*] Post ID: {post_id}")
            
            # Screenshot
            screenshot_path = screenshots_dir / f"{post_id}.png"
            print(f"[*] Taking screenshot: {screenshot_path}")
            
            try:
                if container != page:
                    await container.scroll_into_view_if_needed()
                    await asyncio.sleep(0.5)
                    await container.screenshot(path=str(screenshot_path))
                else:
                    await page.screenshot(path=str(screenshot_path))
            except Exception as e:
                print(f"[!] Screenshot failed: {e}")
                screenshot_path = None

            # External Links
            external_urls = []
            if container != page:
                links = await container.query_selector_all('a[href]')
                for link in links:
                    href = await link.get_attribute('href')
                    if href and ('l.facebook.com' in href or 'youtube.com' in href or 'youtu.be' in href):
                         # Simple extraction, can be improved
                         external_urls.append({'url': href})

            # Save JSON
            json_path = posts_dir / f"{post_id}.json"
            post_data = {
                'id': post_id,
                'handle': handle,
                'profile_url': f"https://www.facebook.com/{handle}",
                'post_url': target_url,
                'external_links': external_urls,
                'screenshot': str(screenshot_path.relative_to(base_dir)) if screenshot_path else None,
                'collected_at': datetime.now().isoformat(),
                'raw_text_preview': clean_text[:1000]
            }
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(post_data, f, ensure_ascii=False, indent=2)
                
            print(f"[*] Saved JSON: {json_path}")
            print("\nDONE.")

    except Exception as e:
        print(f"[!] Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter Facebook Post URL: ")
    
    asyncio.run(scrape_single_post(url))
