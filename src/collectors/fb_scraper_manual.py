"""
Manual Facebook Scraper - Use this when you're already logged in on Facebook
This script will open a browser window where you can manually navigate and it will collect data.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
from playwright.async_api import async_playwright
import re


async def manual_scrape(target_url="https://www.facebook.com/BraterstwaLudziWolnych"):
    """
    Opens browser, waits for you to navigate to FB page, then scrapes.
    """
    base_dir = Path(__file__).parent.parent.parent
    raw_dir = base_dir / "data" / "raw" / "facebook"
    evidence_dir = base_dir / "data" / "evidence" / "facebook"
    raw_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    months_limit = 10
    cutoff_date = datetime.now() - timedelta(days=months_limit * 30)
    
    print("="*60)
    print("MANUAL FACEBOOK SCRAPER")
    print("="*60)
    print(f"\nTarget: {target_url}")
    print("\nInstrukcje:")
    print("1. Otworzy się przeglądarka Chrome")
    print("2. Zaloguj się na Facebook (jeśli nie jesteś)")
    print("3. Zostaniesz przekierowany na docelowy profil")
    print("4. PRZEWIŃ W DÓŁ kilka razy, aby załadować więcej postów")
    print("5. Wróć do terminala i naciśnij ENTER")
    print(f"\nScrapuję posty z ostatnich {months_limit} miesięcy (od {cutoff_date.strftime('%Y-%m-%d')})")
    print("="*60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            channel='chrome'  # Use Chrome
        )
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='pl-PL'
        )
        page = await context.new_page()
        
        # Navigate to target URL
        print(f"\n[*] Otwieranie: {target_url}")
        await page.goto(target_url)
        await asyncio.sleep(3)
        
        print("\n[*] Przeglądarka otwarta!")
        print("[*] Zaloguj się jeśli trzeba")
        print("[*] WAŻNE: Przewiń w dół kilka/kilkanaście razy, aby załadować posty!")
        print("[*] Im więcej przewiniesz, tym więcej postów zbierzemy")
        
        input("\n>>> Naciśnij ENTER gdy przewinąłeś i jesteś gotowy do zbierania danych... ")
        
        # Get current URL
        url = page.url
        print(f"\n[*] Aktualna strona: {url}")
        print("[*] Zbieranie danych...")
        
        # Get page content
        html_content = await page.content()
        
        # Extract profile name
        try:
            title = await page.title()
            name = title.split('|')[0].strip() if '|' in title else title
        except:
            name = "Unknown"
        
        # Extract handle from URL
        handle_match = re.search(r'facebook\.com/([^/?]+)', url)
        handle = handle_match.group(1) if handle_match else "unknown"
        
        print(f"[*] Profil: {name}")
        print(f"[*] Handle: {handle}")
        
        # Extract followers
        followers = None
        try:
            body_text = await page.inner_text('body')
            patterns = [
                r'(\d+(?:\s?\d+)*)\s*obserwuj',
                r'(\d+(?:\s?\d+)*)\s*polubień'
            ]
            for pattern in patterns:
                match = re.search(pattern, body_text, re.IGNORECASE)
                if match:
                    followers = int(match.group(1).replace(' ', ''))
                    break
        except:
            pass
        
        print(f"[*] Obserwujący: {followers if followers else 'nieznane'}")
        
        # Extract posts (not comments)
        print("[*] Wyciąganie postów...")
        posts = []
        
        # Try to find main feed container first
        feed_selectors = [
            'div[role="feed"]',
            'div[data-pagelet*="ProfileTimeline"]',
            'div.x1yztbdb'  # Main feed container
        ]
        
        feed_container = None
        for selector in feed_selectors:
            feed_container = await page.query_selector(selector)
            if feed_container:
                print(f"[*] Znaleziono feed: {selector}")
                break
        
        # Get post elements - only from main feed, not comments
        if feed_container:
            post_elements = await feed_container.query_selector_all('div[data-ad-preview="message"]')
            if not post_elements:
                post_elements = await feed_container.query_selector_all('div[data-ad-comet-preview="message"]')
            if not post_elements:
                # Fallback - get articles but filter out comments
                all_articles = await feed_container.query_selector_all('div[role="article"]')
                post_elements = []
                for article in all_articles:
                    # Skip if it looks like a comment (has comment_id in URL)
                    html = await article.inner_html()
                    if 'comment_id=' not in html and len(html) > 500:
                        post_elements.append(article)
        else:
            print("[!] Nie znaleziono feed containera, używam fallbacku")
            post_elements = await page.query_selector_all('div[role="article"]')
        
        print(f"[*] Znaleziono {len(post_elements)} elementów postów")
        
        collected_texts = set()
        
        for i, post_elem in enumerate(post_elements):
            try:
                text = await post_elem.inner_text()
                
                if not text or len(text) < 20:
                    continue
                
                # Skip if it's clearly a comment (has "Odpowiedz" button text)
                if text.count('Odpowiedz') > 2 or text.startswith('Lubię to!'):
                    continue
                
                # Avoid duplicates
                text_key = text[:100]
                if text_key in collected_texts:
                    continue
                collected_texts.add(text_key)
                
                # Try to extract date
                date_str = None
                date_parsed = None
                time_elements = await post_elem.query_selector_all('a, span')
                
                for elem in time_elements:
                    try:
                        elem_text = await elem.inner_text()
                        if any(word in elem_text.lower() for word in ['godz', 'dni', 'tyg', 'lis', 'paź', 'wrz', 'sie']):
                            date_str = elem_text
                            date_parsed = parse_facebook_date(elem_text)
                            if date_parsed:
                                break
                    except:
                        continue
                
                # Check date limit
                if date_parsed and date_parsed < cutoff_date:
                    print(f"[*] Post #{i+1} jest sprzed {cutoff_date.strftime('%Y-%m-%d')}, pomijam starsze")
                    break
                
                # Extract images
                images = []
                img_elements = await post_elem.query_selector_all('img[src*="scontent"]')
                for img in img_elements[:3]:
                    src = await img.get_attribute('src')
                    if src:
                        images.append(src)
                
                # Extract post URL (skip if it's a comment URL)
                post_url = None
                links = await post_elem.query_selector_all('a[href*="/posts/"], a[href*="/permalink/"], a[href*="/photo/"]')
                for link in links:
                    href = await link.get_attribute('href')
                    if href and 'comment_id=' not in href:
                        post_url = f"https://facebook.com{href}" if href.startswith('/') else href
                        break
                
                post_data = {
                    'text': text[:2000],
                    'date_str': date_str,
                    'date_parsed': date_parsed.isoformat() if date_parsed else None,
                    'post_url': post_url,
                    'images': images,
                    'extracted_at': datetime.now().isoformat()
                }
                
                posts.append(post_data)
                print(f"[+] Post #{len(posts)}: {date_str if date_str else 'data nieznana'}")
            
            except Exception as e:
                print(f"[!] Błąd przy poście #{i+1}: {e}")
                continue
        
        print(f"\n[+] Zebrano {len(posts)} postów")
        
        # Save screenshot
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        screenshot_filename = f"fb_{handle}_{timestamp}.png"
        screenshot_path = evidence_dir / screenshot_filename
        
        print("[*] Zapisywanie screenshota...")
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"[+] Screenshot: {screenshot_path}")
        
        # Save HTML
        html_filename = f"fb_{handle}_{timestamp}.html"
        html_path = raw_dir / html_filename
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"[+] HTML: {html_path}")
        
        # Save JSON
        data = {
            'url': url,
            'scraped_at': datetime.now().isoformat(),
            'scraping_period': f'{months_limit} months',
            'cutoff_date': cutoff_date.isoformat(),
            'name': name,
            'handle': handle,
            'followers': followers,
            'posts': posts,
            'posts_count': len(posts),
            'raw_html_path': str(html_path.relative_to(base_dir)),
            'screenshot_path': str(screenshot_path.relative_to(base_dir))
        }
        
        json_filename = f"fb_{handle}_{timestamp}.json"
        json_path = raw_dir / json_filename
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"[+] JSON: {json_path}")
        
        print("\n" + "="*60)
        print("ZAKOŃCZONO POMYŚLNIE!")
        print("="*60)
        print(f"Profil: {name}")
        print(f"Handle: {handle}")
        print(f"Obserwujący: {followers}")
        print(f"Postów: {len(posts)}")
        print(f"\nPliki zapisane w:")
        print(f"  - {json_path}")
        print(f"  - {screenshot_path}")
        print(f"  - {html_path}")
        print("="*60)
        
        input("\nNaciśnij ENTER aby zamknąć przeglądarkę...")
        
        await browser.close()


def parse_facebook_date(date_str):
    """Parse Facebook date strings (Polish locale)"""
    try:
        date_str = date_str.lower().strip()
        now = datetime.now()
        
        # Hours ago
        if 'godz' in date_str or (date_str.endswith('h') and len(date_str) < 5):
            hours = int(re.search(r'(\d+)', date_str).group(1))
            return now - timedelta(hours=hours)
        
        # Days ago
        if 'dzień' in date_str or 'dni' in date_str or (date_str.endswith('d') and len(date_str) < 5):
            days = int(re.search(r'(\d+)', date_str).group(1))
            return now - timedelta(days=days)
        
        # Weeks ago
        if 'tyg' in date_str or (date_str.endswith('w') and len(date_str) < 5):
            weeks = int(re.search(r'(\d+)', date_str).group(1))
            return now - timedelta(weeks=weeks)
        
        # Polish months
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
                year = now.year
                parsed = datetime(year, month_num, day)
                if parsed > now:
                    parsed = datetime(year - 1, month_num, day)
                return parsed
        
        return None
        
    except:
        return None


if __name__ == "__main__":
    import sys
    print("\nStarting manual Facebook scraper...")
    
    # Allow URL as command line argument
    target = sys.argv[1] if len(sys.argv) > 1 else "https://www.facebook.com/BraterstwaLudziWolnych"
    
    asyncio.run(manual_scrape(target))
