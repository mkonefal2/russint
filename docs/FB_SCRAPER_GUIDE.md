# Facebook Scraper - OSINT Tool

## Wymagania

```bash
pip install playwright beautifulsoup4
playwright install chromium
```

## Użycie

### Podstawowe użycie
```bash
python src/collectors/fb_scraper.py "https://facebook.com/profile_name"
```

### Z widoczną przeglądarką (debugging)
```bash
python src/collectors/fb_scraper.py "https://facebook.com/profile_name" --no-headless
```

### Bez zapisywania screenshotów
```bash
python src/collectors/fb_scraper.py "https://facebook.com/profile_name" --no-screenshots
```

## Co scraper wyciąga?

### Podstawowe dane:
- **Nazwa** profilu/strony
- **Handle** (username)
- **Liczba obserwujących/polubień**
- **Bio/Opis**
- **Zdjęcie profilowe** (URL)
- **Zdjęcie w tle** (URL)
- **Badge weryfikacji** (czy profil jest zweryfikowany)
- **Typ profilu** (osoba prywatna / strona publiczna)

### Posty:
- Ostatnie 10 postów (tekst)
- Data pobrania

### Informacje "O profilu":
- Kategoria (organizacja, osoba publiczna, etc.)
- Dodatkowe info z zakładki "Informacje"

## Struktura zapisywanych plików

### 1. Raw HTML (data/raw/facebook/)
Pełny HTML strony - dowód w postaci oryginalnej.
```
fb_profile-name_20251124_143022.html
```

### 2. Screenshot (data/evidence/facebook/)
Zrzut całej strony.
```
fb_profile-name_20251124_143022.png
```

### 3. Structured JSON (data/raw/facebook/)
Wyekstraktowane dane w formacie JSON:
```json
{
  "url": "https://facebook.com/...",
  "scraped_at": "2025-11-24T14:30:22",
  "profile_type": "page",
  "name": "Fundacja X",
  "handle": "fundacjax",
  "followers": 15000,
  "bio": "Opis działalności...",
  "profile_picture": "https://...",
  "posts": [
    {
      "text": "Treść posta...",
      "extracted_at": "2025-11-24T14:30:22"
    }
  ],
  "verification_badge": false,
  "status": "active",
  "raw_html_path": "data/raw/facebook/fb_fundacjax_20251124_143022.html",
  "screenshot_path": "data/evidence/facebook/fb_fundacjax_20251124_143022.png"
}
```

## Ograniczenia i uwagi

### Facebook często zmienia strukturę HTML
Ten scraper używa ogólnych selektorów, ale FB regularnie aktualizuje swój DOM. Może wymagać dostosowania.

### Rate limiting
Facebook ma mechanizmy anty-botowe:
- Używaj z opóźnieniami między requestami
- Nie scrape'uj dziesiątek profili pod rząd
- Rozważ użycie proxy/VPN dla większych operacji

### Logowanie
Ten scraper działa **bez logowania** - wyciąga tylko publicznie dostępne dane. Dla większości celów OSINT to wystarcza.

Jeśli potrzebujesz danych spoza publicznych:
1. Użyj narzędzi typu **mbasic.facebook.com** (lżejsza wersja FB)
2. Rozważ użycie sesji z ciasteczkami zalogowanego użytkownika (etyczne i prawne zastrzeżenia!)

### Legalność
**WAŻNE:** Ten skrypt jest do celów OSINT - zbierania publicznie dostępnych informacji. Nie używaj go do:
- Zbierania danych prywatnych
- Naruszania regulaminu FB w sposób bezprawny
- Stalkingu lub nękania

## Dalsze kroki

Po zebraniu danych możesz:
1. Użyć LLM do ekstrakcji kluczowych informacji z JSON
2. Zaimportować dane do głównych szablonów (`organization_template.json`, `individual_template.json`)
3. Analizować powiązania między profilami

## Przykładowy workflow

```bash
# 1. Scrape profilu
python src/collectors/fb_scraper.py "https://facebook.com/fundacjax"

# 2. Przejrzyj JSON w data/raw/facebook/
# 3. Wyciągnij kluczowe dane i użyj LLM do wypełnienia template
# 4. Zapisz finalny JSON do data/processed/org-fundacja-x.json
```

## Troubleshooting

### "Timeout error"
- Zwiększ timeout w kodzie (linia: `timeout=30000`)
- Sprawdź połączenie internetowe
- FB może blokować - użyj VPN

### "Element not found"
- FB zmienił strukturę - zaktualizuj selektory
- Profil może być prywatny lub usunięty

### Browser nie startuje
```bash
playwright install chromium
```

## TODO / Możliwe rozszerzenia
- [ ] Scraping komentarzy pod postami
- [ ] Ekstrakcja linków z bio
- [ ] Analiza czasowa aktywności (kiedy publikują)
- [ ] Scraping listy znajomych/fanów (jeśli publiczne)
- [ ] Integracja z Telegram/Twitter scraperami
