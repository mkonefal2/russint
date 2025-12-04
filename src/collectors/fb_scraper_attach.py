"""
Facebook Scraper - Connect to existing Chrome instance
This connects to Chrome running with --remote-debugging-port=9222
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
import asyncio
from playwright.async_api import async_playwright
import re


async def scrape_current_page():
    """
    Connects to existing Chrome and scrapes whatever page is currently open.
    """
    base_dir = Path(__file__).parent.parent.parent
    raw_dir = base_dir / "data" / "raw" / "facebook"
    evidence_dir = base_dir / "data" / "evidence" / "facebook"
    raw_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    
    months_limit = 10
    cutoff_date = datetime.now() - timedelta(days=months_limit * 30)
    
    print("="*60)
    print("FACEBOOK SCRAPER - ATTACH TO CHROME")
    print("="*60)
    print("\nInstrukcje:")
    print("1. W juz otwartym Chrome przejdz do profilu FB")
    print("2. [!] WAZNE: RECZNIE przewin strone w dol wielokrotnie,")
    print("   az zaladuja sie posty z ostatnich 10 miesiecy")
    print("   (Facebook NIE laduje postow przy automatycznym scrollowaniu)")
    print("3. Wroc tutaj i nacisnij ENTER")
    print(f"\nScrapuje posty z ostatnich {months_limit} miesiecy")
    print("="*60)
    
    input("\n>>> Naciśnij ENTER gdy RĘCZNIE przewinąłeś profil w Chrome... ")
    
    try:
        async with async_playwright() as p:
            print("\n[*] Łączenie z Chrome...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            
            # Get the first context (default)
            if not browser.contexts:
                print("[!] Brak otwartych kontekstów w Chrome")
                return
            
            context = browser.contexts[0]
            
            # Get active page
            pages = context.pages
            if not pages:
                print("[!] Brak otwartych zakładek")
                return
            
            page = pages[0]  # First tab
            
            print(f"[*] Połączono! Aktualna strona: {page.url}")
            
            url = page.url
            
            # Check if it's Facebook
            if 'facebook.com' not in url:
                print("[!] To nie jest strona Facebook!")
                print(f"[!] Aktualna strona: {url}")
                cont = input("Kontynuować mimo to? (y/n): ")
                if cont.lower() != 'y':
                    return
            
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
                    r'(\d+(?:\s?\d+)*)\s*polubień',
                    r'([\d\s]+)\s*follower'
                ]
                for pattern in patterns:
                    match = re.search(pattern, body_text, re.IGNORECASE)
                    if match:
                        followers = int(match.group(1).replace(' ', '').replace(',', ''))
                        break
            except:
                pass
            
            print(f"[*] Obserwujący: {followers if followers else 'nieznane'}")
            
            # Timestamp dla nazw plików - generujemy raz na początku
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Get page HTML (bez scrollowania - użytkownik już przewinął)
            print("[*] Pobieram HTML strony...")
            html_content = await page.content()
            
            # --- WYCIĄGANIE POSTÓW Z DOM (nie JSON) ---
            print("[*] Wyciąganie postów z DOM...")
            
            posts = []
            collected_texts = set()
            collected_urls = set()
            
            # Facebook używa wirtualizacji - posty są ładowane gdy są widoczne
            # Musimy przewinąć do każdego kontenera aby załadować jego zawartość
            
            # Szukaj kontenerów postów: div z aria-posinset
            post_containers = await page.query_selector_all('div[aria-posinset]')
            print(f"    Znaleziono {len(post_containers)} kontenerów postów")
            print(f"    Przewijam przez wszystkie kontenery aby załadować treść...")
            
            # FAZA 1: Przewiń przez wszystkie kontenery aby je dewirtualizować
            for container in post_containers:
                try:
                    await container.scroll_into_view_if_needed()
                    await asyncio.sleep(0.15)
                except:
                    pass
            
            # Poczekaj chwilę na załadowanie wszystkiego
            await asyncio.sleep(1)
            print(f"    Dewirtualizacja zakończona, pobieram treść...")
            
            # FAZA 2: Teraz zbieraj dane
            for i, container in enumerate(post_containers):
                try:
                    # Sprawdź czy kontener ma treść (po przewinięciu)
                    full_text = await container.inner_text()
                    
                    # Pomiń bardzo krótkie (puste kontenery)
                    if len(full_text) < 30:
                        continue
                    
                    # Pomiń jeśli to tylko "Facebook Facebook..." (niezaładowany)
                    if full_text.replace('Facebook', '').replace('\n', '').strip() == '':
                        continue
                    
                    # Wyciągnij URL posta
                    post_url = None
                    
                    # Szukaj linków do postów, video, zdjęć
                    link_selectors = [
                        'a[href*="/posts/"]',
                        'a[href*="/permalink/"]', 
                        'a[href*="/videos/"]',
                        'a[href*="/photos/"]',
                        'a[href*="/watch/"]'
                    ]
                    
                    for selector in link_selectors:
                        links = await container.query_selector_all(selector)
                        for link in links:
                            href = await link.get_attribute('href')
                            if href:
                                # Pomiń linki do komentarzy
                                if 'comment_id=' in href or 'reply_comment_id=' in href:
                                    continue
                                
                                # Wyczyść URL
                                clean_url = href.split('?')[0] if '?' in href else href
                                post_url = f"https://facebook.com{clean_url}" if clean_url.startswith('/') else clean_url
                                break
                        if post_url:
                            break
                    
                    # Deduplikacja po URL
                    if post_url:
                        if post_url in collected_urls:
                            continue
                        collected_urls.add(post_url)
                    else:
                        # Fallback: deduplikacja po treści (środkowa część)
                        text_key = full_text[100:250] if len(full_text) > 250 else full_text[:150]
                        text_key = text_key.replace('\n', ' ').strip()
                        if text_key in collected_texts:
                            continue
                        collected_texts.add(text_key)
                    
                    # Wyciągnij główny tekst postu
                    post_text = ""
                    
                    # Strategia 1: data-ad-comet-preview (główny tekst postu)
                    main_text_div = await container.query_selector('div[data-ad-comet-preview="message"]')
                    if not main_text_div:
                        main_text_div = await container.query_selector('div[data-ad-preview="message"]')
                    
                    if main_text_div:
                        post_text = await main_text_div.inner_text()
                    
                    # Strategia 2: Szukaj treści w różnych miejscach
                    if not post_text or len(post_text) < 10:
                        text_divs = await container.query_selector_all('div[dir="auto"]')
                        
                        for div in text_divs[:15]:  # Sprawdź więcej elementów
                            try:
                                # Sprawdź czy to nie jest część komentarzy
                                is_comment = await div.evaluate("""el => {
                                    const article = el.closest('[role="article"]');
                                    if (article) {
                                        const label = article.getAttribute('aria-label');
                                        return label && label.includes('Komentarz');
                                    }
                                    return false;
                                }""")
                                if is_comment:
                                    continue
                                
                                div_text = await div.inner_text()
                                
                                # Pomiń UI elementy
                                if any(x in div_text for x in ['Lubię to', 'Komentuj', 'Udostępnij', 'Like', 'Comment', 'Share', 'Wszystkie reakcje']):
                                    continue
                                
                                # Pomiń "Facebook" spam
                                if div_text.replace('Facebook', '').replace('\n', '').strip() == '':
                                    continue
                                
                                if len(div_text) > len(post_text) and len(div_text) < 5000:
                                    post_text = div_text
                            except:
                                continue
                    
                    # Strategia 3: Szukaj zewnętrznych linków (YouTube, artykuły)
                    external_link_title = None
                    external_url = None
                    
                    # Szukaj podglądu linku (YouTube, artykuł)
                    link_preview = await container.query_selector('a[href*="youtube.com"], a[href*="youtu.be"], a[role="link"][href*="l.facebook.com"]')
                    if link_preview:
                        external_url = await link_preview.get_attribute('href')
                        # Tytuł podglądu jest często w span obok
                        title_span = await container.query_selector('span[dir="auto"]')
                        if title_span:
                            external_link_title = await title_span.inner_text()
                    
                    # Jeśli nie mamy tekstu ale mamy tytuł linku, użyj go
                    if (not post_text or len(post_text) < 10) and external_link_title:
                        post_text = external_link_title
                    
                    if not post_text:
                        # Fallback: Weź początek full_text (przed sekcją reakcji)
                        cutoff_markers = ['Lubię to', 'Wszystkie reakcje', 'Komentarz', 'Udostępnij']
                        for marker in cutoff_markers:
                            if marker in full_text:
                                candidate = full_text.split(marker)[0]
                                # Usuń śmieci na początku (Facebook Facebook...)
                                lines = candidate.split('\n')
                                clean_lines = [l for l in lines if l.strip() and l.strip() != 'Facebook']
                                post_text = '\n'.join(clean_lines[-10:])  # Ostatnie 10 linii przed reakcjami
                                break
                        
                        if not post_text:
                            post_text = full_text[:500]
                    
                    # Wyciągnij datę - szukaj tylko krótkich elementów zawierających datę
                    # WAŻNE: Szukaj w HEADERZE postu, NIE w sekcji komentarzy
                    date_str = None
                    date_parsed = None
                    
                    # Szukamy daty w linkach i spanach (odfiltrowanie komentarzy)
                    all_links = await container.query_selector_all('a[href*="/posts/"], a[href*="/videos/"], a[href*="/photos/"]')
                    all_spans = await container.query_selector_all('span')
                    
                    potential_date_elems = list(all_links[:10]) + list(all_spans[:200])
                    
                    for elem in potential_date_elems:
                        try:
                            elem_text = await elem.inner_text()
                        except:
                            continue
                            
                        elem_text = elem_text.strip()
                        elem_lower = elem_text.lower()
                        
                        # Pomiń puste, "Facebook" lub długie teksty
                        if not elem_text or elem_text == "Facebook" or len(elem_text) > 50:
                            continue
                            
                        # Sprawdź czy to komentarz
                        try:
                            is_comment = await elem.evaluate("""el => {
                                const link = el.closest('a');
                                return link && (link.href.includes('comment_id') || link.href.includes('reply_comment_id'));
                            }""")
                            if is_comment:
                                continue
                        except:
                            pass
                        
                        # WZORCE DAT
                        date_patterns = [
                            # Pełna data "25 września", "10 października", "3 lip"
                            r'^(\d{1,2})\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|października|listopada|grudnia)$',
                            r'^(\d{1,2})\s+(sty|lut|mar|kwi|maj|cze|lip|sie|wrz|paź|paz|lis|gru)\.?$',
                            # Względne: "5 godz", "3 dni", "8 tyg"
                            r'^(\d+)\s*(godz|h)\.?$',
                            r'^(\d+)\s*(dni|d)\.?$',
                            r'^(\d+)\s*(tyg|w)\.?$',
                            # "wczoraj", "Wczoraj"
                            r'^wczoraj$',
                        ]
                        
                        for pattern in date_patterns:
                            if re.match(pattern, elem_lower):
                                date_str = elem_text
                                date_parsed = parse_facebook_date(elem_text)
                                break
                        
                        if date_parsed:
                            break
                    
                    # Sprawdź date limit
                    if date_parsed and date_parsed < cutoff_date:
                        print(f"    Post #{i+1} jest sprzed cutoff date, pomijam starsze")
                        break
                    
                    # Wyciągnij obrazy
                    images = []
                    imgs = await container.query_selector_all('img[src*="scontent"]')
                    for img in imgs[:3]:  # Max 3 obrazy
                        src = await img.get_attribute('src')
                        if src:
                            images.append(src)
                    
                    # Screenshot pojedynczego posta
                    post_screenshot_path = None
                    try:
                        # Przewiń do posta aby był widoczny
                        await container.scroll_into_view_if_needed()
                        await asyncio.sleep(0.3)  # Poczekaj na załadowanie
                        
                        # Zrób screenshot kontenera posta
                        post_num = len(posts) + 1
                        post_screenshot_filename = f"fb_{handle}_{timestamp}_post{post_num:03d}.png"
                        post_screenshot_path = evidence_dir / post_screenshot_filename
                        
                        await container.screenshot(path=str(post_screenshot_path))
                        print(f"    Screenshot posta #{post_num}: {post_screenshot_filename}")
                    except Exception as e:
                        print(f"    [!] Nie udało się zrobić screenshota posta: {e}")
                    
                    post_data = {
                        'text': post_text[:2000] if post_text else full_text[:500],
                        'date': date_str,
                        'timestamp': date_parsed.isoformat() if date_parsed else None,
                        'url': post_url if post_url else f"https://www.facebook.com/{handle}",
                        'author': name,
                        'images': images,
                        'external_url': external_url if external_url else None,
                        'screenshot': str(post_screenshot_path.relative_to(base_dir)) if post_screenshot_path and post_screenshot_path.exists() else None
                    }
                    
                    posts.append(post_data)
                    print(f"    Zebrano post #{len(posts)}: {date_str if date_str else 'brak daty'}")
                    
                except Exception as e:
                    print(f"    Błąd przy article #{i}: {e}")
                    continue
            
            print(f"[+] Zebrano {len(posts)} postów z DOM")
            
            # Save full page screenshot (opcjonalnie - jako backup)
            screenshot_filename = f"fb_{handle}_{timestamp}_full.png"
            screenshot_path = evidence_dir / screenshot_filename
            
            print("[*] Zapisywanie screenshota całej strony (opcjonalnie)...")
            try:
                await page.screenshot(path=str(screenshot_path), full_page=True)
                print(f"[+] Screenshot całej strony: {screenshot_path}")
            except Exception as e:
                print(f"[!] Nie udało się zapisać screenshota całej strony: {e}")
                print("    (To nie problem - screenshoty postów zostały zapisane)")
            
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
            
            print("\n[*] Chrome pozostaje otwarty - możesz kontynuować przeglądanie")
    
    except Exception as e:
        print(f"\n[!] Błąd: {e}")
        print("\nUpewnij się, że Chrome jest uruchomiony z:")
        print('chrome.exe --remote-debugging-port=9222')
        import traceback
        traceback.print_exc()


def parse_facebook_date(date_str):
    """Parse Facebook date strings (Polish locale)"""
    try:
        date_str = date_str.lower().strip()
        now = datetime.now()
        
        # "wczoraj"
        if 'wczoraj' in date_str:
            return now - timedelta(days=1)
        
        # Hours ago: "5 godz", "5h", "5 godz."
        if 'godz' in date_str or (date_str.endswith('h') and len(date_str) < 5):
            match = re.search(r'(\d+)', date_str)
            if match:
                hours = int(match.group(1))
                return now - timedelta(hours=hours)
        
        # Minutes ago: "5 min"
        if 'min' in date_str:
            match = re.search(r'(\d+)', date_str)
            if match:
                minutes = int(match.group(1))
                return now - timedelta(minutes=minutes)
        
        # Days ago: "3 dni", "3d", "1 dzień"
        if 'dzień' in date_str or 'dni' in date_str or (date_str.endswith('d') and len(date_str) < 5):
            match = re.search(r'(\d+)', date_str)
            if match:
                days = int(match.group(1))
                return now - timedelta(days=days)
        
        # Weeks ago: "8 tyg", "8 tyg.", "8w"
        if 'tyg' in date_str or (date_str.endswith('w') and len(date_str) < 5):
            match = re.search(r'(\d+)', date_str)
            if match:
                weeks = int(match.group(1))
                return now - timedelta(weeks=weeks)
        
        # Polish months - full and abbreviated
        months_pl = {
            'stycznia': 1, 'sty': 1, 'styczeń': 1,
            'lutego': 2, 'lut': 2, 'luty': 2,
            'marca': 3, 'mar': 3, 'marzec': 3,
            'kwietnia': 4, 'kwi': 4, 'kwiecień': 4,
            'maja': 5, 'maj': 5,
            'czerwca': 6, 'cze': 6, 'czerwiec': 6,
            'lipca': 7, 'lip': 7, 'lipiec': 7,
            'sierpnia': 8, 'sie': 8, 'sierpień': 8,
            'września': 9, 'wrz': 9, 'wrzesień': 9,
            'października': 10, 'paź': 10, 'paz': 10, 'październik': 10,
            'listopada': 11, 'lis': 11, 'listopad': 11,
            'grudnia': 12, 'gru': 12, 'grudzień': 12
        }
        
        for month_name, month_num in months_pl.items():
            if month_name in date_str:
                match = re.search(r'(\d+)', date_str)
                if match:
                    day = int(match.group(1))
                    year = now.year
                    try:
                        parsed = datetime(year, month_num, day)
                        if parsed > now:
                            parsed = datetime(year - 1, month_num, day)
                        return parsed
                    except ValueError:
                        continue
        
        return None
        
    except:
        return None


if __name__ == "__main__":
    print("\nFacebook Scraper - Attach to Chrome")
    print("Upewnij się, że Chrome jest uruchomiony z:")
    print("  chrome.exe --remote-debugging-port=9222\n")
    asyncio.run(scrape_current_page())
