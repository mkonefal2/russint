import asyncio
import json
import os
import re
import csv
from datetime import datetime
from playwright.async_api import async_playwright
import urllib.parse

# Load keywords from dictionary file
DICTIONARY_PATH = "data/dictionaries/suspicious_keywords.json"

def load_keywords():
    if not os.path.exists(DICTIONARY_PATH):
        print(f"Warning: Dictionary file not found at {DICTIONARY_PATH}. Using default keywords.")
        return None, None

    with open(DICTIONARY_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    search_tags = ["RADICAL_ORGANIZATION", "NATIONALIST_IDEOLOGY", "SABOTAGE_EUPHEMISMS", "HISTORICAL_MARKERS"]
    
    # Return full objects for danger analysis to access tags
    search_keywords = list(set([item['term'] for item in data if any(tag in item['tags'] for tag in search_tags)]))
    danger_objects = [item for item in data] # Keep all for analysis
    
    return search_keywords, danger_objects

loaded_search, loaded_danger_objects = load_keywords()

# Keywords to search for channels (Google/DDG search)
SEARCH_KEYWORDS = loaded_search if loaded_search else [
    "dywersja", "sabotaż", "opór", "akcja bezpośrednia", 
    "partyzantka", "legion", "batalion", "ruch oporu"
]

# Scoring configuration
TAG_SCORES = {
    "DIRECT": 50,
    "SABOTAGE_EUPHEMISMS": 50,
    "RECRUITMENT_PAYMENT": 40,
    "INFRASTRUCTURE_TARGETS": 30,
    "SECURITY_OPSEC": 20,
    "RUSSIAN_UKRAINIAN_RECRUITMENT": 30,
    "RECRUITMENT_SELECTION": 10,
    "RADICAL_ORGANIZATION": 10,
    "NATIONALIST_IDEOLOGY": 5,
    "HISTORICAL_MARKERS": 5,
    "SYMBOLS_CODES": 10,
    "VERIFICATION_CONTROL": 20
}

RISK_THRESHOLD = 60

def analyze_message(text, danger_objects):
    """
    Analyze message text and calculate risk score based on keywords and their tags.
    Returns (score, matched_keywords, matched_tags)
    """
    if not text:
        return 0, [], []
        
    text_lower = text.lower()
    score = 0
    matched_keywords = []
    matched_tags = set()
    
    # Check for each keyword in the dictionary
    for item in danger_objects:
        term = item['term'].lower()
        if term in text_lower:
            # Avoid double counting if one term is substring of another (simple approach: just count all)
            # or if term is very short and common (e.g. "14") - might need boundary check
            
            # Basic word boundary check for short terms
            if len(term) < 4:
                if not re.search(r'\b' + re.escape(term) + r'\b', text_lower):
                    continue
            
            matched_keywords.append(item['term'])
            
            # Add score for each tag of this term
            term_score = 0
            for tag in item['tags']:
                matched_tags.add(tag)
                term_score = max(term_score, TAG_SCORES.get(tag, 0)) # Take max score of tags for this term
            
            score += term_score

    # Bonus for combinations
    if "RECRUITMENT_PAYMENT" in matched_tags and "INFRASTRUCTURE_TARGETS" in matched_tags:
        score += 30
    if "RECRUITMENT_PAYMENT" in matched_tags and "SABOTAGE_EUPHEMISMS" in matched_tags:
        score += 40
    if "SECURITY_OPSEC" in matched_tags and "RECRUITMENT_PAYMENT" in matched_tags:
        score += 20

    return score, list(set(matched_keywords)), list(matched_tags)

OUTPUT_DIR = "data/raw/telegram"

async def search_channels(page, keyword):
    """Search for Telegram channels using Google"""
    print(f"Searching for: {keyword}...")
    # Broader query without "polska" restriction, requesting more results
    query = f'site:t.me {keyword}'
    url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&num=20"
    
    try:
        await page.goto(url)
        
        # Handle consent forms
        try:
            await page.get_by_role("button", name=re.compile(r"(Zaakceptuj|Accept|Zgadzam|Agree)", re.IGNORECASE)).click(timeout=3000)
        except:
            pass
            
        await asyncio.sleep(3) # Wait for results to load
        
        # Check for CAPTCHA
        if await page.locator('text=recaptcha').count() > 0 or await page.locator('text=robot').count() > 0:
            print("  [!] Google CAPTCHA detected. Please solve it manually in the browser window.")
            await asyncio.sleep(15) # Give user time to solve
        
        # Get all links
        links = await page.evaluate('''() => {
            const anchors = Array.from(document.querySelectorAll('a'));
            return anchors.map(a => a.href);
        }''')
        
        telegram_links = []
        for link in links:
            if "t.me/" in link:
                # Handle both t.me/username and t.me/s/username
                # We want to capture the username part
                match = re.search(r't\.me/(?:s/)?([a-zA-Z0-9_]+)', link)
                if match:
                    username = match.group(1)
                    # Filter out system paths
                    if username.lower() not in ['s', 'share', 'sticker', 'addstickers', 'joinchat', 'iv', 'contact', 'login']:
                        telegram_links.append(f"https://t.me/s/{username}")
        
        unique_links = list(set(telegram_links))
        print(f"  Found {len(unique_links)} unique Telegram links")
        return unique_links
        
    except Exception as e:
        print(f"Error searching for {keyword}: {e}")
        return []

async def scrape_channel_preview(page, channel_url):
    """Scrape the public preview of a Telegram channel"""
    print(f"Scraping channel: {channel_url}")
    try:
        await page.goto(channel_url)
        await page.wait_for_selector('.tgme_widget_message', timeout=5000)
        
        # Scroll up a bit to load more messages if possible (Telegram preview loads older on scroll up usually, 
        # but for simple preview we just take what's there)
        
        channel_data = await page.evaluate('''() => {
            const titleEl = document.querySelector('.tgme_channel_info_header_title');
            const title = titleEl ? titleEl.innerText : 'Unknown';
            
            const messages = [];
            const msgElements = document.querySelectorAll('.tgme_widget_message');
            
            msgElements.forEach(el => {
                const textEl = el.querySelector('.tgme_widget_message_text');
                const dateEl = el.querySelector('.tgme_widget_message_date time');
                const linkEl = el.querySelector('.tgme_widget_message_date');
                
                if (textEl) {
                    messages.push({
                        text: textEl.innerText,
                        date: dateEl ? dateEl.getAttribute('datetime') : null,
                        url: linkEl ? linkEl.href : null
                    });
                }
            });
            
            return { title, messages };
        }''')
        
        return channel_data
        
    except Exception as e:
        print(f"Error scraping {channel_url}: {e}")
        return None

async def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False) # Headless=False to see what's happening/avoid some bot detection
        page = await browser.new_page()
        
        all_channels = set()
        
        # 1. Search phase
        for keyword in SEARCH_KEYWORDS:
            links = await search_channels(page, keyword)
            print(f"Found {len(links)} links for '{keyword}'")
            all_channels.update(links)
            await asyncio.sleep(2) # Be nice
            
        print(f"\nTotal unique channels found: {len(all_channels)}")
        
        # 2. Scrape phase
        flat_results = []
        
        for channel_url in all_channels:
            data = await scrape_channel_preview(page, channel_url)
            
            if data:
                channel_has_matches = False
                for msg in data['messages']:
                    score, keywords, tags = analyze_message(msg['text'], loaded_danger_objects)
                    
                    if score > 0:
                        print(f"  [+] Match in {data['title']}: '{', '.join(keywords)}' (Score: {score})")
                        channel_has_matches = True
                        flat_results.append({
                            'channel_title': data['title'],
                            'channel_url': channel_url.replace('/s/', '/'),
                            'message_url': msg['url'],
                            'date': msg['date'],
                            'risk_score': score,
                            'found_keywords': ", ".join(keywords),
                            'found_tags': ", ".join(tags),
                            'text_snippet': msg['text'][:200].replace('\n', ' ') if msg['text'] else ""
                        })
                
                # If no matches found in the whole preview, still save the channel
                if not channel_has_matches:
                     print(f"  [i] Scraped {data['title']} - No keywords found")
                     flat_results.append({
                        'channel_title': data['title'],
                        'channel_url': channel_url.replace('/s/', '/'),
                        'message_url': channel_url,
                        'date': datetime.now().isoformat(),
                        'risk_score': 0,
                        'found_keywords': "",
                        'found_tags': "",
                        'text_snippet': "No suspicious keywords found in recent messages"
                    })
            else:
                print(f"  [!] Failed to scrape {channel_url}")
                # Failed to scrape or empty
                flat_results.append({
                    'channel_title': "Unknown/Error",
                    'channel_url': channel_url.replace('/s/', '/'),
                    'message_url': "",
                    'date': datetime.now().isoformat(),
                    'risk_score': 0,
                    'found_keywords': "",
                    'found_tags': "",
                    'text_snippet': "Could not scrape channel preview"
                })
            
            await asyncio.sleep(1)

        # 3. Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(OUTPUT_DIR, f"telegram_web_scan_{timestamp}.csv")
        
        if flat_results:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=['channel_title', 'channel_url', 'message_url', 'date', 'risk_score', 'found_keywords', 'found_tags', 'text_snippet'])
                writer.writeheader()
                writer.writerows(flat_results)
            
            print(f"\nScan complete. Results saved to {filename}")
        else:
            print(f"\nScan complete. No suspicious content found.")
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
