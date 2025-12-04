"""
Facebook Scraper v2 - Uproszczony
Każdy post = osobny JSON + screenshot z tym samym ID

Wymaga Chrome uruchomionego z:
  chrome.exe --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome-debug"
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
import asyncio
from playwright.async_api import async_playwright
import re


async def scrape_posts():
    """
    Łączy się z Chrome i zbiera posty z aktualnie otwartej strony FB.
    Każdy post zapisuje jako osobny JSON + screenshot.
    Automatycznie scrolluje stronę aby załadować posty.
    """
    base_dir = Path(__file__).parent.parent.parent
    posts_dir = base_dir / "data" / "raw" / "facebook" / "posts"
    screenshots_dir = base_dir / "data" / "evidence" / "facebook" / "screenshots"
    posts_dir.mkdir(parents=True, exist_ok=True)
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    
    print("="*60)
    print("FACEBOOK SCRAPER v2 - AUTO-SCROLL")
    print("="*60)
    print("\nInstrukcje:")
    print("1. Uruchom Chrome z: chrome.exe --remote-debugging-port=9222 --user-data-dir=\"%TEMP%\\chrome-debug\"")
    print("2. Przejdź do profilu FB który chcesz scrapować")
    print("3. Scraper SAM przewinie stronę i załaduje posty")
    print("4. Naciśnij ENTER tutaj")
    print("="*60)
    
    input("\n>>> Naciśnij ENTER gdy gotowy... ")
    
    try:
        async with async_playwright() as p:
            print("\n[*] Łączenie z Chrome...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            
            if not browser.contexts:
                print("[!] Brak kontekstów w Chrome")
                return
            
            context = browser.contexts[0]
            pages = context.pages
            
            if not pages:
                print("[!] Brak otwartych zakładek")
                return
            
            page = pages[0]
            url = page.url
            
            print(f"[*] Strona: {url}")
            
            if 'facebook.com' not in url:
                print("[!] To nie jest Facebook!")
                return
            
            # Wyciągnij handle z URL
            handle_match = re.search(r'facebook\.com/([^/?]+)', url)
            handle = handle_match.group(1) if handle_match else "unknown"
            print(f"[*] Handle: {handle}")
            
            # === KATALOGI DLA KONKRETNEGO PROFILU ===
            # Struktura: data/raw/facebook/{handle}/...
            posts_dir = base_dir / "data" / "raw" / "facebook" / handle
            screenshots_dir = base_dir / "data" / "evidence" / "facebook" / handle
            posts_dir.mkdir(parents=True, exist_ok=True)
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            print(f"[*] Zapisuję do: {posts_dir}")
            
            # Timestamp sesji
            session_ts = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # === ZBIERANIE PODCZAS SCROLLOWANIA ===
            print("[*] Scrollowanie i zbieranie postów...")
            collected_ids = set()  # Zebrane post IDs (deduplikacja)
            collected_urls = {}  # URL -> post_id (sprawdzanie duplikatów URL)
            posts_saved = 0
            no_new_posts_count = 0
            max_scrolls = 100  # Maksymalnie 100 przewinięć
            last_scroll_position = 0
            same_position_count = 0
            duplicate_url_count = 0  # Licznik duplikatów URL
            
            for scroll_num in range(max_scrolls):
                # Pobierz wszystkie widoczne kontenery
                post_containers = await page.query_selector_all('div[aria-posinset]')
                
                new_posts_this_scroll = 0
                skipped_duplicates = 0
                
                print(f"\n  [Scroll {scroll_num+1}] Znaleziono {len(post_containers)} kontenerów...")
                
                for container in post_containers:
                    try:
                        # === DEDUPLIKACJA PO aria-posinset (indeks posta na FB) ===
                        posinset = await container.get_attribute('aria-posinset')
                        if posinset and posinset in collected_ids:
                            skipped_duplicates += 1
                            continue
                        
                        # Sprawdź czy kontener ma treść
                        full_text = await container.inner_text()
                        clean_text = full_text.replace('Facebook', '').replace('\n', '').strip()
                        if len(clean_text) < 20:
                            continue
                        
                        # Dodaj do zebranych
                        if posinset:
                            collected_ids.add(posinset)
                        
                        # Przewiń dokładnie do tego posta
                        await container.scroll_into_view_if_needed()
                        await asyncio.sleep(0.2)  # Szybszy scroll
                        
                        # === WYCIĄGNIJ URL POSTA ===
                        post_url = None
                        inner_html = await container.inner_html()
                        
                        # Metoda 0: JavaScript - znajdź WŁASNY link pfbid dla tego posta (STRICT bounding box)
                        try:
                            post_url = await container.evaluate('''(el) => {
                                // Pobierz bounding box tego kontenera
                                const myRect = el.getBoundingClientRect();
                                const myTop = myRect.top;
                                const myBottom = myRect.bottom;
                                
                                // Idź w górę i szukaj wszystkich linków pfbid
                                let current = el;
                                for (let i = 0; i < 10; i++) {
                                    if (!current.parentElement) break;
                                    current = current.parentElement;
                                }
                                
                                // Znajdź wszystkie linki pfbid
                                const allLinks = current.querySelectorAll('a[href*="pfbid"]');
                                
                                // Znajdź link którego pozycja jest WEWNĄTRZ naszego kontenera (STRICT)
                                for (const link of allLinks) {
                                    const href = link.getAttribute('href');
                                    if (!href || href.includes('comment_id=')) continue;
                                    
                                    const linkRect = link.getBoundingClientRect();
                                    const linkTop = linkRect.top;
                                    
                                    // Link musi być DOKŁADNIE wewnątrz kontenera (bez fallback!)
                                    if (linkTop >= myTop && linkTop <= myBottom) {
                                        return href.split('?')[0];
                                    }
                                }
                                
                                // NIE MA FALLBACK - zwróć null jeśli nie znaleziono
                                return null;
                            }''')
                        except Exception as e:
                            print(f"      [DEBUG] Metoda 0 error: {e}")
                        
                        # RETRY: Jeśli nie znaleziono, szukaj linku timestamp (drugi lub trzeci link z __cft__)
                        if not post_url:
                            try:
                                # Znajdź wszystkie linki z __cft__ - timestamp to zwykle 2-4 link
                                cft_links = await container.query_selector_all('a[href*="__cft__"]')
                                
                                # Pomiń pierwszy (to profil), weź następne
                                for i, link in enumerate(cft_links[1:5] if len(cft_links) > 1 else []):
                                    href = await link.get_attribute('href')
                                    # Szukaj linku który jest WZGLĘDNY (zaczyna się od ?) - to timestamp
                                    if href and href.startswith('?'):
                                        await link.hover()
                                        await asyncio.sleep(0.15)
                                        
                                        # Sprawdź czy po hover pojawił się pfbid
                                        post_url = await container.evaluate('''(el) => {
                                            const myRect = el.getBoundingClientRect();
                                            const myTop = myRect.top;
                                            const myBottom = myRect.bottom;
                                            
                                            let current = el;
                                            for (let i = 0; i < 10; i++) {
                                                if (!current.parentElement) break;
                                                current = current.parentElement;
                                            }
                                            
                                            const allLinks = current.querySelectorAll('a[href*="pfbid"]');
                                            
                                            for (const link of allLinks) {
                                                const href = link.getAttribute('href');
                                                if (!href || href.includes('comment_id=')) continue;
                                                const linkRect = link.getBoundingClientRect();
                                                if (linkRect.top >= myTop - 50 && linkRect.top <= myBottom + 50) {
                                                    return href.split('?')[0];
                                                }
                                            }
                                            return null;
                                        }''')
                                        
                                        if post_url:
                                            break
                                
                                # Reset hover
                                await container.hover()
                            except:
                                pass
                        
                        # Metoda 1: Szukaj linków z pfbid wewnątrz kontenera
                        pfbid_links = await container.query_selector_all('a[href*="pfbid"]')
                        for link in pfbid_links:
                            href = await link.get_attribute('href')
                            if href and 'comment_id=' not in href:
                                clean_href = href.split('?')[0]
                                if 'pfbid' in clean_href:
                                    post_url = clean_href
                                    break
                        
                        # Metoda 2: Szukaj po standardowych ścieżkach
                        if not post_url:
                            link_selectors = [
                                'a[href*="/posts/"]',
                                'a[href*="/permalink/"]', 
                                'a[href*="/videos/"]',
                                'a[href*="/photos/"]',
                            ]
                            for selector in link_selectors:
                                links = await container.query_selector_all(selector)
                                for link in links:
                                    href = await link.get_attribute('href')
                                    if href and 'comment_id=' not in href:
                                        clean_href = href.split('?')[0]
                                        if clean_href.startswith('/'):
                                            post_url = f"https://www.facebook.com{clean_href}"
                                        else:
                                            post_url = clean_href
                                        break
                                if post_url:
                                    break
                        
                        # Metoda 3: Regex na HTML - szukaj pfbid (cyfry LUB litery po pfbid)
                        if not post_url:
                            pfbid_match = re.search(r'pfbid[0-9a-zA-Z]{20,}', inner_html)
                            if pfbid_match:
                                post_url = f"https://www.facebook.com/{handle}/posts/{pfbid_match.group(0)}"
                        
                        # Metoda 4: Szukaj linku w timestamp (aria-label z datą)
                        if not post_url:
                            # Szukaj linków które mają aria-label lub są w pobliżu tekstu z datą
                            time_links = await container.query_selector_all('a[role="link"]')
                            for link in time_links:
                                href = await link.get_attribute('href')
                                aria = await link.get_attribute('aria-label')
                                if href and aria:
                                    # Aria-label zawierające datę/czas
                                    if any(x in aria.lower() for x in ['godz', 'min', 'dni', 'hour', 'day', 'minute', 'lis', 'paź', 'wrz', 'sie', 'lip', 'cze', 'maj', 'kwi', 'mar', 'lut', 'sty']):
                                        if 'facebook.com' in href or href.startswith('/'):
                                            clean_href = href.split('?')[0]
                                            if clean_href.startswith('/'):
                                                post_url = f"https://www.facebook.com{clean_href}"
                                            else:
                                                post_url = clean_href
                                            break
                        
                        # Metoda 5: Szukaj story_fbid w URL
                        if not post_url:
                            story_match = re.search(r'story_fbid=(\d+)', inner_html)
                            if story_match:
                                id_match = re.search(r'id=(\d+)', inner_html)
                                if id_match:
                                    post_url = f"https://www.facebook.com/permalink.php?story_fbid={story_match.group(1)}&id={id_match.group(1)}"
                        
                        # Metoda 6: Szukaj KAŻDEGO linku z handle w href
                        if not post_url:
                            all_links = await container.query_selector_all('a[href]')
                            for link in all_links:
                                href = await link.get_attribute('href')
                                if href and handle in href:
                                    # Szukaj linków które wyglądają jak permalink
                                    if '/posts/' in href or '/permalink' in href or 'pfbid' in href or 'story_fbid' in href:
                                        clean_href = href.split('?')[0]
                                        if clean_href.startswith('/'):
                                            post_url = f"https://www.facebook.com{clean_href}"
                                        else:
                                            post_url = clean_href
                                        break
                        
                        # Metoda 7: Regex - szukaj wszystkich wzorców FB URL w HTML
                        if not post_url:
                            # story_fbid w dowolnym formacie
                            patterns = [
                                rf'/{handle}/posts/[a-zA-Z0-9]+',
                                rf'/{handle}/videos/[0-9]+',
                                rf'/{handle}/photos/[a-zA-Z0-9/.]+',
                                r'permalink\.php\?story_fbid=[0-9]+&amp;id=[0-9]+',
                                r'story_fbid%3D([0-9]+).*?id%3D([0-9]+)',
                            ]
                            for pattern in patterns:
                                match = re.search(pattern, inner_html)
                                if match:
                                    found = match.group(0).replace('&amp;', '&')
                                    if found.startswith('/'):
                                        post_url = f"https://www.facebook.com{found}"
                                    elif 'permalink' in found:
                                        post_url = f"https://www.facebook.com/{found}"
                                    elif '%3D' in found:
                                        # URL-encoded story_fbid
                                        sid = re.search(r'story_fbid%3D([0-9]+)', found)
                                        iid = re.search(r'id%3D([0-9]+)', found)
                                        if sid and iid:
                                            post_url = f"https://www.facebook.com/permalink.php?story_fbid={sid.group(1)}&id={iid.group(1)}"
                                    else:
                                        post_url = f"https://www.facebook.com{found}"
                                    break
                        
                        # === LINKI ZEWNĘTRZNE ===
                        external_urls = []
                        seen_urls = set()
                        
                        # YouTube
                        yt_links = await container.query_selector_all('a[href*="youtube.com/watch"], a[href*="youtu.be/"]')
                        for link in yt_links:
                            href = await link.get_attribute('href')
                            if href:
                                clean_url = href.split('&fbclid=')[0]
                                if 'l.facebook.com' in clean_url:
                                    url_match = re.search(r'u=([^&]+)', clean_url)
                                    if url_match:
                                        from urllib.parse import unquote
                                        clean_url = unquote(url_match.group(1)).split('&fbclid=')[0]
                                if clean_url not in seen_urls:
                                    seen_urls.add(clean_url)
                                    external_urls.append({'type': 'youtube', 'url': clean_url})
                        
                        # Inne linki zewnętrzne
                        ext_links = await container.query_selector_all('a[href*="l.facebook.com/l.php"]')
                        for link in ext_links:
                            href = await link.get_attribute('href')
                            if href:
                                url_match = re.search(r'u=([^&]+)', href)
                                if url_match:
                                    from urllib.parse import unquote
                                    decoded_url = unquote(url_match.group(1)).split('&fbclid=')[0]
                                    if 'youtube.com' not in decoded_url and 'youtu.be' not in decoded_url:
                                        if decoded_url not in seen_urls:
                                            seen_urls.add(decoded_url)
                                            external_urls.append({'type': 'article', 'url': decoded_url})
                        
                        # === ID POSTA (uniwersalne: source_handle_unique) ===
                        posts_saved += 1
                        source = "fb"  # Facebook
                        
                        # Użyj pfbid jako ID jeśli dostępny, inaczej hash contentu
                        if post_url and 'pfbid' in post_url:
                            # Wyciągnij pfbid z URL
                            pfbid_match = re.search(r'pfbid([0-9a-zA-Z]+)', post_url)
                            if pfbid_match:
                                unique_id = f"pfbid{pfbid_match.group(1)}"
                            else:
                                unique_id = f"h{hash(clean_text[:200]) & 0xFFFFFFFF:08x}"
                        else:
                            # Fallback: hash z treści
                            unique_id = f"h{hash(clean_text[:200]) & 0xFFFFFFFF:08x}"
                        
                        post_id = f"{source}_{handle}_{unique_id}"
                        
                        # === SPRAWDŹ CZY JUŻ ISTNIEJE ===
                        json_path = posts_dir / f"{post_id}.json"
                        if json_path.exists():
                            print(f"    [SKIP] {post_id} już istnieje")
                            continue
                        
                        # === SCREENSHOT ===
                        screenshot_path = screenshots_dir / f"{post_id}.png"
                        try:
                            await container.screenshot(path=str(screenshot_path))
                        except:
                            screenshot_path = None
                        
                        # === DEBUG: Zapisz HTML jeśli brak URL ===
                        if not post_url:
                            debug_dir = base_dir / "data" / "debug"
                            debug_dir.mkdir(parents=True, exist_ok=True)
                            debug_path = debug_dir / f"{post_id}_debug.html"
                            with open(debug_path, 'w', encoding='utf-8') as f:
                                f.write(inner_html)
                        
                        # === ZAPISZ JSON ===
                        post_data = {
                            'id': post_id,
                            'handle': handle,
                            'profile_url': url,
                            'post_url': post_url,
                            'external_links': external_urls if external_urls else None,
                            'screenshot': str(screenshot_path.relative_to(base_dir)) if screenshot_path else None,
                            'collected_at': datetime.now().isoformat(),
                            'raw_text_preview': clean_text[:500] if clean_text else None
                        }
                        
                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump(post_data, f, ensure_ascii=False, indent=2)
                        
                        # === CHECK DUPLIKATY URL ===
                        is_duplicate = False
                        if post_url:
                            if post_url in collected_urls:
                                duplicate_url_count += 1
                                is_duplicate = True
                            else:
                                collected_urls[post_url] = post_id
                        
                        new_posts_this_scroll += 1
                        ext_info = f" + {len(external_urls)} ext" if external_urls else ""
                        url_short = post_url[-30:] if post_url else "BRAK"
                        dup_mark = " ⚠️DUP!" if is_duplicate else ""
                        print(f"    [{posts_saved}] {post_id} -> {url_short}{ext_info}{dup_mark}")
                        
                    except Exception as e:
                        continue
                
                # Przewiń w dół
                await page.evaluate('window.scrollBy(0, window.innerHeight * 1.5)')
                await asyncio.sleep(0.5)
                
                # Sprawdź aktualną pozycję scrolla
                current_scroll = await page.evaluate('window.scrollY')
                
                print(f"    -> Nowe: {new_posts_this_scroll}, Pominięte: {skipped_duplicates}, Scroll: {current_scroll:.0f}px")
                
                # Sprawdź czy scroll się zatrzymał (koniec strony)
                if current_scroll == last_scroll_position:
                    same_position_count += 1
                    if same_position_count >= 3:
                        print(f"\n[*] Scroll się zatrzymał - koniec strony")
                        break
                else:
                    same_position_count = 0
                    last_scroll_position = current_scroll
                
                # Sprawdź czy są nowe posty
                if new_posts_this_scroll == 0:
                    no_new_posts_count += 1
                    if no_new_posts_count >= 8:
                        print(f"\n[*] Brak nowych postów po 8 scrollach - koniec")
                        break
                else:
                    no_new_posts_count = 0
            
            print(f"\n{'='*60}")
            print(f"ZAKOŃCZONO - zapisano {posts_saved} postów")
            if duplicate_url_count > 0:
                print(f"⚠️  UWAGA: {duplicate_url_count} duplikatów URL!")
            print(f"Unikalne URL: {len(collected_urls)}")
            print(f"{'='*60}")
            print(f"Posty JSON: {posts_dir}")
            print(f"Screenshoty: {screenshots_dir}")
            print(f"{'='*60}")
            
    except Exception as e:
        print(f"\n[!] Błąd: {e}")
        print("\nUpewnij się że Chrome jest uruchomiony z:")
        print('  chrome.exe --remote-debugging-port=9222 --user-data-dir="%TEMP%\\chrome-debug"')
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(scrape_posts())
