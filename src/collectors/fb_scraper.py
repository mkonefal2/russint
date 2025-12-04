"""
Facebook Profile Scraper for OSINT purposes
Extracts public information from Facebook profiles and pages.

Requirements:
- playwright (browser automation)
- beautifulsoup4 (HTML parsing)
- json, datetime (built-in)

Usage:
    python fb_scraper.py "https://facebook.com/profile_name" --use-edge
    python fb_scraper.py "https://facebook.com/profile_name" --months 10
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
import argparse
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
from bs4 import BeautifulSoup
import re


class FacebookScraper:
    def __init__(self, headless=True, save_screenshots=True, use_edge_session=False, months_limit=10):
        self.headless = headless
        self.save_screenshots = save_screenshots
        self.use_edge_session = use_edge_session
        self.months_limit = months_limit
        self.base_dir = Path(__file__).parent.parent.parent
        self.raw_dir = self.base_dir / "data" / "raw" / "facebook"
        self.evidence_dir = self.base_dir / "data" / "evidence" / "facebook"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate cutoff date
        self.cutoff_date = datetime.now() - timedelta(days=months_limit * 30)

    async def scrape_profile(self, url):
        """
        Scrapes a Facebook profile/page and returns structured data.
        Limited to posts from last N months.
        """
        print(f"[*] Starting scrape of: {url}")
        print(f"[*] Limit: Posts from last {self.months_limit} months (since {self.cutoff_date.strftime('%Y-%m-%d')})")
        
        async with async_playwright() as p:
            # Use existing Edge session via CDP or launch new browser
            if self.use_edge_session:
                print("[*] Connecting to existing Edge session via CDP...")
                print("[!] Make sure Edge is running with: msedge.exe --remote-debugging-port=9222")
                
                try:
                    browser = await p.chromium.connect_over_cdp("http://localhost:9222")
                    context = browser.contexts[0]
                    page = await context.new_page()
                except Exception as e:
                    print(f"[!] Failed to connect to Edge CDP: {e}")
                    print("[*] Falling back to new browser instance...")
                    self.use_edge_session = False
            
            if not self.use_edge_session:
                # Launch fresh browser
                browser = await p.chromium.launch(
                    headless=self.headless,
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox'
                    ]
                )
                
                context = await browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='pl-PL'
                )
                
                page = await context.new_page()
            
            try:
                # Navigate to profile
                print("[*] Loading page...")
                await page.goto(url, wait_until='networkidle', timeout=30000)
                await asyncio.sleep(3)  # Wait for dynamic content
                
                # Close cookie banner if exists
                try:
                    cookie_button = await page.query_selector('button[data-cookiebanner="accept_button"]')
                    if cookie_button:
                        await cookie_button.click()
                        await asyncio.sleep(1)
                except:
                    pass
                
                # Intelligent scrolling - stop when we hit date limit
                print("[*] Scrolling to load posts (limited by date)...")
                posts_collected = await self._scroll_and_collect_posts(page, max_posts=100)
                
                # Get page content
                html_content = await page.content()
                soup = BeautifulSoup(html_content, 'html.parser')
                
                # Extract data
                data = {
                    'url': url,
                    'scraped_at': datetime.now().isoformat(),
                    'scraping_period': f'{self.months_limit} months',
                    'cutoff_date': self.cutoff_date.isoformat(),
                    'profile_type': self._detect_profile_type(url),
                    'name': await self._extract_name(page, soup),
                    'handle': self._extract_handle(url),
                    'followers': await self._extract_followers(page, soup),
                    'bio': await self._extract_bio(page, soup),
                    'profile_picture': await self._extract_profile_picture(page),
                    'cover_photo': await self._extract_cover_photo(page),
                    'posts': posts_collected,
                    'posts_count': len(posts_collected),
                    'about_info': await self._extract_about_info(page, soup),
                    'page_info': await self._extract_page_info(page, soup),
                    'verification_badge': await self._check_verification(page),
                    'status': 'active',
                    'raw_html_path': None,
                    'screenshot_path': None
                }
                
                # Save screenshot
                if self.save_screenshots:
                    screenshot_filename = f"fb_{self._sanitize_filename(data['handle'])}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                    screenshot_path = self.evidence_dir / screenshot_filename
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    data['screenshot_path'] = str(screenshot_path.relative_to(self.base_dir))
                    print(f"[+] Screenshot saved: {screenshot_path}")
                
                # Save raw HTML
                html_filename = f"fb_{self._sanitize_filename(data['handle'])}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                html_path = self.raw_dir / html_filename
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(html_content)
                data['raw_html_path'] = str(html_path.relative_to(self.base_dir))
                print(f"[+] Raw HTML saved: {html_path}")
                
                # Save structured JSON
                json_filename = f"fb_{self._sanitize_filename(data['handle'])}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                json_path = self.raw_dir / json_filename
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"[+] JSON saved: {json_path}")
                
                return data
                
            except PlaywrightTimeout:
                print("[!] Timeout error - page took too long to load")
                return None
            except Exception as e:
                print(f"[!] Error during scraping: {str(e)}")
                import traceback
                traceback.print_exc()
                return None
            finally:
                if self.use_edge_session:
                    try:
                        await page.close()
                    except:
                        pass
                else:
                    try:
                        await browser.close()
                    except:
                        pass

    def _detect_profile_type(self, url):
        """Detect if it's a personal profile or a page"""
        if '/pages/' in url or '/profile.php' not in url and '/people/' not in url:
            return 'page'
        return 'profile'

    async def _extract_name(self, page, soup):
        """Extract profile/page name"""
        try:
            # Try multiple selectors
            name_element = await page.query_selector('h1')
            if name_element:
                return await name_element.inner_text()
            
            # Fallback to title
            title = await page.title()
            if title and '|' in title:
                return title.split('|')[0].strip()
            
            return title or "Unknown"
        except:
            return "Unknown"

    def _extract_handle(self, url):
        """Extract username/handle from URL"""
        # Extract from URL patterns
        patterns = [
            r'facebook\.com/([^/?]+)',
            r'fb\.com/([^/?]+)'
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return "unknown"

    async def _extract_followers(self, page, soup):
        """Extract follower/likes count"""
        try:
            # Look for follower count patterns
            text = await page.inner_text('body')
            
            # Polish patterns
            patterns = [
                r'(\d+(?:\s?\d+)*)\s*obserwuj',
                r'(\d+(?:\s?\d+)*)\s*polubień',
                r'(\d+(?:\s?\d+)*)\s*followers',
                r'(\d+(?:[\s,]\d+)*)\s*likes'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    count_str = match.group(1).replace(' ', '').replace(',', '')
                    return int(count_str)
            
            return None
        except:
            return None

    async def _extract_bio(self, page, soup):
        """Extract bio/description"""
        try:
            # Try to find intro section
            selectors = [
                'div[data-pagelet="ProfileTilesFeed_0"]',
                'div.x1gslohp',
                'div[role="article"]'
            ]
            
            for selector in selectors:
                element = await page.query_selector(selector)
                if element:
                    text = await element.inner_text()
                    if text and len(text) > 20:
                        return text[:500]  # Limit length
            
            return ""
        except:
            return ""

    async def _extract_profile_picture(self, page):
        """Extract profile picture URL"""
        try:
            img = await page.query_selector('image')
            if img:
                return await img.get_attribute('xlink:href')
            return None
        except:
            return None

    async def _extract_cover_photo(self, page):
        """Extract cover photo URL"""
        try:
            # Cover photos are usually large images
            imgs = await page.query_selector_all('img')
            for img in imgs[:5]:  # Check first few images
                src = await img.get_attribute('src')
                if src and ('cover' in src.lower() or 'scontent' in src):
                    return src
            return None
        except:
            return None

    async def _scroll_and_collect_posts(self, page, max_posts=100):
        """
        Intelligent scrolling that collects posts until date limit or max count.
        """
        posts = []
        collected_urls = set()  # Track URLs to avoid duplicates
        last_height = 0
        scroll_attempts = 0
        max_scroll_attempts = 20
        
        print(f"[*] Collecting posts (max: {max_posts}, date limit: {self.cutoff_date.strftime('%Y-%m-%d')})")
        
        while len(posts) < max_posts and scroll_attempts < max_scroll_attempts:
            # Scroll down
            await page.evaluate('window.scrollBy(0, window.innerHeight)')
            await asyncio.sleep(3)  # Wait for content to load
            
            # Get all post elements
            post_elements = await page.query_selector_all('div[role="article"]')
            print(f"[*] Found {len(post_elements)} post elements on page...")
            
            for post_elem in post_elements:
                if len(posts) >= max_posts:
                    break
                    
                try:
                    post_data = await self._extract_post_data(post_elem)
                    
                    if post_data:
                        # Use URL or text hash to avoid duplicates
                        unique_key = post_data.get('post_url') or hash(post_data['text'][:100])
                        
                        if unique_key not in collected_urls:
                            collected_urls.add(unique_key)
                            
                            # Check date if available
                            if post_data.get('date_parsed'):
                                if post_data['date_parsed'] < self.cutoff_date:
                                    print(f"[*] Reached date limit. Stopping at post from {post_data['date_str']}")
                                    return posts
                            
                            posts.append(post_data)
                            print(f"[+] Collected post #{len(posts)}: {post_data.get('date_str', 'date unknown')}")
                
                except Exception as e:
                    print(f"[!] Error extracting post: {e}")
                    continue
            
            # Check if we've scrolled to the bottom
            new_height = await page.evaluate('document.body.scrollHeight')
            if new_height == last_height:
                scroll_attempts += 1
                print(f"[*] No new content loaded (attempt {scroll_attempts}/{max_scroll_attempts})")
            else:
                scroll_attempts = 0
                last_height = new_height
        
        print(f"[+] Collection complete: {len(posts)} posts")
        return posts

    async def _extract_post_data(self, post_element):
        """Extract data from a single post element"""
        try:
            text = await post_element.inner_text()
            
            if not text or len(text) < 10:
                return None
            
            # Try to extract date/time
            date_str = None
            date_parsed = None
            
            # Look for time elements
            time_elements = await post_element.query_selector_all('a[href*="/posts/"], span[id^="jsc_"], abbr')
            for elem in time_elements:
                try:
                    date_text = await elem.inner_text()
                    date_parsed = self._parse_facebook_date(date_text)
                    if date_parsed:
                        date_str = date_text
                        break
                except:
                    continue
            
            # Extract images if present
            images = []
            img_elements = await post_element.query_selector_all('img[src*="scontent"]')
            for img in img_elements[:3]:  # Max 3 images per post
                src = await img.get_attribute('src')
                if src:
                    images.append(src)
            
            # Extract post URL if available
            post_url = None
            link_elements = await post_element.query_selector_all('a[href*="/posts/"], a[href*="/permalink/"]')
            if link_elements:
                href = await link_elements[0].get_attribute('href')
                if href:
                    post_url = f"https://facebook.com{href}" if href.startswith('/') else href
            
            return {
                'text': text[:2000],  # Limit text length
                'date_str': date_str,
                'date_parsed': date_parsed,
                'post_url': post_url,
                'images': images,
                'extracted_at': datetime.now().isoformat()
            }
        
        except Exception as e:
            return None

    def _parse_facebook_date(self, date_str):
        """
        Parse Facebook date strings (Polish locale)
        Examples: "5 godz.", "2 dni", "3 tyg.", "1 listopada", "1 lis"
        """
        try:
            date_str = date_str.lower().strip()
            now = datetime.now()
            
            # Hours ago
            if 'godz' in date_str or 'h' == date_str[-1]:
                hours = int(re.search(r'(\d+)', date_str).group(1))
                return now - timedelta(hours=hours)
            
            # Days ago
            if 'dzień' in date_str or 'dni' in date_str or 'd' == date_str[-1]:
                days = int(re.search(r'(\d+)', date_str).group(1))
                return now - timedelta(days=days)
            
            # Weeks ago
            if 'tyg' in date_str or 'w' == date_str[-1]:
                weeks = int(re.search(r'(\d+)', date_str).group(1))
                return now - timedelta(weeks=weeks)
            
            # Months - Polish month names
            months_pl = {
                'stycznia': 1, 'sty': 1,
                'lutego': 2, 'lut': 2,
                'marca': 3, 'mar': 3,
                'kwietnia': 4, 'kwi': 4,
                'maja': 5, 'maj': 5,
                'czerwca': 6, 'cze': 6,
                'lipca': 7, 'lip': 7,
                'sierpnia': 8, 'sie': 8,
                'września': 9, 'wrz': 9,
                'października': 10, 'paź': 10,
                'listopada': 11, 'lis': 11,
                'grudnia': 12, 'gru': 12
            }
            
            for month_name, month_num in months_pl.items():
                if month_name in date_str:
                    day = int(re.search(r'(\d+)', date_str).group(1))
                    # Assume current year unless in future
                    year = now.year
                    parsed = datetime(year, month_num, day)
                    if parsed > now:
                        parsed = datetime(year - 1, month_num, day)
                    return parsed
            
            return None
            
        except:
            return None

    async def _extract_about_info(self, page, soup):
        """Extract about information"""
        try:
            # Try to navigate to About section
            about_link = await page.query_selector('a[href*="/about"]')
            if about_link:
                await about_link.click()
                await asyncio.sleep(2)
                
                text = await page.inner_text('body')
                return text[:1000]  # Return first 1000 chars
            
            return ""
        except:
            return ""

    async def _extract_page_info(self, page, soup):
        """Extract page-specific info (category, etc)"""
        try:
            info = {}
            text = await page.inner_text('body')
            
            # Try to find category
            if 'Organizacja' in text or 'Organization' in text:
                info['category'] = 'organization'
            elif 'Osoba publiczna' in text or 'Public Figure' in text:
                info['category'] = 'public_figure'
            
            return info
        except:
            return {}

    async def _check_verification(self, page):
        """Check if profile has verification badge"""
        try:
            # Look for verification badge
            badge = await page.query_selector('svg[aria-label*="Verified"]')
            return badge is not None
        except:
            return False

    def _sanitize_filename(self, filename):
        """Sanitize filename for safe file saving"""
        return re.sub(r'[^\w\-_.]', '_', filename)


async def main():
    parser = argparse.ArgumentParser(description='Scrape Facebook profiles for OSINT')
    parser.add_argument('url', help='Facebook profile/page URL')
    parser.add_argument('--use-edge', action='store_true',
                       help='Use existing Edge browser session (must be logged in)')
    parser.add_argument('--months', type=int, default=10,
                       help='Number of months to scrape back (default: 10)')
    parser.add_argument('--headless', action='store_true', default=False, 
                       help='Run browser in headless mode (default: False)')
    parser.add_argument('--no-screenshots', action='store_true', 
                       help='Disable screenshot capture')
    
    args = parser.parse_args()
    
    # Force headless=False if using Edge session
    if args.use_edge:
        args.headless = False
    
    scraper = FacebookScraper(
        headless=args.headless,
        save_screenshots=not args.no_screenshots,
        use_edge_session=args.use_edge,
        months_limit=args.months
    )
    
    result = await scraper.scrape_profile(args.url)
    
    if result:
        print("\n" + "="*50)
        print("SCRAPING COMPLETED SUCCESSFULLY")
        print("="*50)
        print(f"Name: {result['name']}")
        print(f"Handle: {result['handle']}")
        print(f"Followers: {result['followers']}")
        print(f"Verification: {'Yes' if result['verification_badge'] else 'No'}")
        print(f"Posts extracted: {result['posts_count']}")
        print(f"Scraping period: {result['scraping_period']}")
        print(f"\nData saved to:")
        print(f"  JSON: {result['raw_html_path'].replace('.html', '.json')}")
        print(f"  HTML: {result['raw_html_path']}")
        print(f"  Screenshot: {result['screenshot_path']}")
    else:
        print("\n[!] Scraping failed")


if __name__ == "__main__":
    asyncio.run(main())
