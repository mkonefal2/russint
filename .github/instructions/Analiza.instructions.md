---
applyTo: '**'
---

# Instrukcja dla LLM: Przepływ Analizy Screenshot → Neo4j

## 📋 PRZEGLĄD PROCESU

Gdy użytkownik prosi o analizę screenshotu z Facebooka, wykonujesz następujący workflow:

```
Screenshot FB → Analiza LLM → JSON (graph_nodes + graph_edges) → Neo4j Aura
```

## 🎯 KROK 1: ODBIÓR DANYCH WEJŚCIOWYCH

Użytkownik dostarcza:
- **Screenshot** posta z Facebooka (`.png` lub `.jpg`)
- **Opcjonalnie:** Plik JSON ze scrapera (`fb_scraper_v2.py`) zawierający:
  - `id` - unikalny identyfikator posta
  - `raw_text_preview` - tekst posta
  - `post_url` - link do posta
  - `handle` - nazwa profilu
  - `collected_at` - data zescrapowania
  - `screenshot` - **ścieżka względna** do pliku screenshotu (np. `data/evidence/facebook/BraterstwaLudziWolnych/post_123.png`)

### Lokalizacje plików:
```
data/
  raw/
    facebook/
      [handle]/           ← JSONy dla konkretnego profilu (nowa struktura)
      posts/              ← JSONy z pojedynczych postów (stara struktura)
  evidence/
    facebook/
      [handle]/           ← Screenshoty dla konkretnego profilu
      screenshots/        ← Screenshoty postów (stara struktura)
```

### 🔗 Zasada parowania (Matching):
Pliki JSON i Screenshoty są powiązane tym samym identyfikatorem (`id` posta).
- Jeśli masz plik JSON `[id].json`, szukaj odpowiadającego mu screenshotu `[id].png` (lub `.jpg`) w folderze `evidence`.
- Analizując screenshot, zawsze sprawdzaj, czy istnieje odpowiadający mu plik JSON z metadanymi (URL, data, tekst).

## 🔍 KROK 2: ANALIZA VISION (GPT-4o/Claude)

### Prompt systemowy:
Wczytaj plik: `docs/LLM_ANALYSIS_PROMPT.md`

### Co analizujesz ze screenshotu:
1. **Tekst widoczny na obrazie** (często różni się od JSON - może zawierać memy, grafiki z tekstem)
2. **Osoby wymienione** (imiona, nazwiska, pseudonimy)
3. **Organizacje** (nazwy grup, stowarzyszeń, partii)
4. **Wydarzenia** (protesty, zloty, konferencje)
5. **Profil/Strona** (autor posta)
6. **Post** (sam post jako node w grafie)
7. **Symbole i grafiki** (flagi, loga, naszywki)
8. **URL-e** (linki do innych stron, Sputnik, RT, YouTube)

### Co analizujesz z JSON:
1. `id` - klucz główny dla posta
2. `raw_text_preview` - treść tekstowa
3. `handle` - profil/strona autora
4. `post_url` - **WAŻNE: zawsze dodawaj ten URL do entity typu 'post'**
5. `collected_at` - timestamp
6. `screenshot` - nazwa pliku screenshotu (dla referencji)

## 📝 KROK 3: EKSTRAKCJA ENTITIES (NODES)

Dla każdej zidentyfikowanej encji tworzysz obiekt JSON zgodnie ze schematem:

### Schema: `data/raw/graph_nodes.json` (Seed Data)

> **Uwaga:** Ten plik służy teraz jako dane startowe (seed). Nowe analizy zapisuj w osobnych plikach w `data/processed/graph_increments/`.

```json
[
  {
    "id": "org-braterstwa-ludzi-wolnych",
    "entity_type": "organization",
    "name": "Braterstwa Ludzi Wolnych",
    "description": "Organizacja promująca narracje anty-systemowe",
    "country": "PL",
    "first_seen": "2024-01-15",
    "notes": "Aktywni na FB, organizują zloty"
  },
  {
    "id": "profile-braterstwa-ludzi-wolnych",
    "entity_type": "profile",
    "name": "FB: Braterstwa Ludzi Wolnych",
    "platform": "facebook",
    "url": "https://www.facebook.com/BraterstwaLudziWolnych",
    "handle": "BraterstwaLudziWolnych",
    "parent_org_id": "org-braterstwa-ludzi-wolnych"
  },
  {
    "id": "post-001",
    "entity_type": "post",
    "name": "Post: Harmonogram Spotkania Rodzin (25.06.2025)",
    "platform": "facebook",
    "url": "https://www.facebook.com/BraterstwaLudziWolnych/posts/pfbid0219rwE34d48hfcTuUrccvvxgFizYcByeXwMTjzbrD9dX1ycUz9PvANH2Kw4KAJSN5l",
    "description": "Ogłoszenie wydarzenia z listą prelegentów",
    "date_posted": "2025-06-20"
  },
  {
    "id": "evt-001",
    "entity_type": "event",
    "name": "Spotkanie Rodzin Po Bratersku 2025",
    "date_start": "2025-06-25",
    "date_end": "2025-06-29",
    "location": "Gmina Białowieża"
  },
  {
    "id": "ent-002",
    "entity_type": "person",
    "name": "Jakub Kuśpit",
    "description": "Prelegent na wydarzeniu"
  }
]
```

### Typy encji (`entity_type`):
- `organization` - organizacja/stowarzyszenie (abstrakcyjny podmiot)
- `profile` - profil/strona na platformie (FB, Twitter, TikTok)
- `person` - osoba fizyczna
- `event` - wydarzenie (protest, zlot, konferencja)
- `post` - pojedynczy post w mediach społecznościowych
- `page` - strona internetowa
- `group` - grupa na FB/Telegram
- `channel` - kanał YouTube/Telegram

### Zasady generowania ID:
```python
# Organizacja
"org-{normalized_name}"  # org-braterstwa-ludzi-wolnych

# Osoba
"ent-{numer}"            # ent-002 (używaj numeracji sekwencyjnej)

# Profil
"profile-{numer}"        # profile-braterstwa-ludzi-wolnych

# Event
"evt-{numer}"            # evt-001

# Post
"post-{numer}"           # post-001
```

### Nazewnictwo węzłów (`name`)

- **Ważne:** pole `name` dla węzła `Post` musi być opisowe i informować, o czym jest post (krótka fraza/teza), a nie zawierać jedynie informacji technicznej typu "screenshot" lub "repost".
- Przykład dobrego `name`: "Post: ABW wtargnęła do naszych domów o 6 rano" lub "Repost: twierdzenia o 'PsyOp' i 'pseudo-elity' (udostępnienie Jakuba Kuśpita)".
- Unikaj umieszczania w `name` długich identyfikatorów; identyfikatory przechowuj w polu `id`.

## 🔗 KROK 4: EKSTRAKCJA RELATIONSHIPS (EDGES)

Dla każdego połączenia między encjami tworzysz relację:

### Schema: `data/raw/graph_edges.json` (Seed Data)

> **Uwaga:** Ten plik służy teraz jako dane startowe (seed). Nowe analizy zapisuj w osobnych plikach w `data/processed/graph_increments/`.

```json
[
  {
    "source_id": "org-braterstwa-ludzi-wolnych",
    "target_id": "profile-braterstwa-ludzi-wolnych",
    "relationship_type": "HAS_PROFILE",
    "source_name": "Braterstwa Ludzi Wolnych",
    "target_name": "FB: Braterstwa Ludzi Wolnych",
    "date": "2024-01-15",
    "confidence": 1.0,
    "evidence": "Oficjalny profil organizacji"
  },
  {
    "source_id": "profile-braterstwa-ludzi-wolnych",
    "target_id": "post-001",
    "relationship_type": "PUBLISHED",
    "source_name": "FB: Braterstwa Ludzi Wolnych",
    "target_name": "Post: Harmonogram Spotkania Rodzin",
    "date": "2025-06-20",
    "confidence": 1.0,
    "evidence": "Post opublikowany na profilu"
  },
  {
    "source_id": "ent-002",
    "target_id": "evt-001",
    "relationship_type": "SPEAKER_AT",
    "source_name": "Jakub Kuśpit",
    "target_name": "Spotkanie Rodzin Po Bratersku 2025",
    "confidence": 1.0,
    "evidence": "Wymieniony jako prelegent w poście"
  }
]
```

### Typy relacji (`relationship_type`):
- `HAS_PROFILE` - organizacja → profil na platformie
- `PUBLISHED` - profil → post (kto opublikował post)
- `ANNOUNCES` - post → event (post ogłasza wydarzenie)
- `ORGANIZES` - organizacja → event (kto organizuje)
- `SPEAKER_AT` - osoba → event (prelegent/uczestnik)
- `MENTIONS` - neutralne wspomnienie
- `PROMOTES` - pozytywna promocja
- `ATTACKS` - negatywna krytyka
- `REPOSTS` - udostępnienie posta
- `SHARES_CONTENT_FROM` - udostępnienie treści z innego źródła
- `MEMBER_OF` - członkostwo w organizacji
- `COLLABORATES_WITH` - współpraca
- `LINKS_TO` - post/strona linkuje do innej strony
- `FEATURED_ON` - osoba/organizacja występuje w mediach
- `WORKS_AT` - zatrudnienie
- `AFFILIATED_WITH` - powiązanie (ogólne)

### Confidence Level:
```
1.0 = Pewność 100% (bezpośrednie źródło)
0.8 = Bardzo prawdopodobne
0.6 = Prawdopodobne
0.4 = Możliwe
0.2 = Spekulacja
```

## 💾 KROK 5: ZAPISYWANIE DANYCH

### Nowy Standard (Incremental Loading)

Zamiast dopisywać do dużych plików zbiorczych, zapisz wynik analizy jako **nowy, osobny plik JSON** w folderze `data/processed/graph_increments/`.

**Nazwa pliku:** `analysis_[post_id].json` (np. `analysis_fb_BraterstwaLudziWolnych_pfbid0x8...json`)

**Struktura pliku:**
```json
{
  "meta": {
    "source_file": "fb_BraterstwaLudziWolnych_pfbid0x8...json",
    "analyzed_at": "2025-11-26T12:00:00"
  },
  "nodes": [
    {
      "id": "post-001",
      "entity_type": "post",
      "name": "...",
      "country": "PL",
      ...
    },
    ...
  ],
  "edges": [
    {
      "source_id": "profile-braterstwa-ludzi-wolnych",
      "target_id": "post-001",
      "relationship_type": "PUBLISHED",
      ...
    },
    ...
  ]
}
```

### Procedura zapisu:
1. Wygeneruj JSON z polami `nodes` i `edges`.
2. Zapisz go w `data/processed/graph_increments/`.
3. Uruchom skrypt `python scripts/load_to_neo4j.py`, który automatycznie wykryje nowy plik i załaduje go do bazy.

### Opcja B: Użyj Streamlit UI (Legacy)
...existing code...

```bash
streamlit run src/ui/post_viewer_app.py
```

Interfejs pozwala:
- Przeglądać posty i screenshoty
- Edytować graf w zakładce "Graph Editor"
- Synchronizować z Neo4j jednym kliknięciem

## ☁️ KROK 6: MIGRACJA DO NEO4J AURA

### Automatyczna migracja:

```bash
python scripts/load_to_neo4j.py
```

### Co robi skrypt:

1. **Wczytuje dane z JSON:**
   - `data/raw/graph_nodes.json`
   - `data/raw/graph_edges.json`

2. **Czyści bazę Neo4j** (usuwa stare dane)

3. **Tworzy ograniczenia** (unique ID dla każdego typu)

4. **Ładuje węzły:**
```cypher
MERGE (n:Organization {id: $id})
SET n += $props
```

5. **Ładuje relacje:**
```cypher
MATCH (source {id: $source_id})
MATCH (target {id: $target_id})
MERGE (source)-[r:SPEAKER_AT]->(target)
SET r += $props
```

6. **Wyświetla statystyki:**
   - Liczba węzłów wg typu
   - Liczba relacji wg typu
   - Top węzły (najwyższy stopień)

## 🔍 KROK 7: WERYFIKACJA W NEO4J

### Sprawdź dane:
```bash
python scripts/check_neo4j_data.py
```

### Neo4j Explore (UI):
```
https://console-preview.neo4j.io/
```

### Przykładowe zapytania Cypher:

```cypher
// Wyświetl wszystkie węzły i relacje
MATCH p=(n)-[r]->(m) 
RETURN p 
LIMIT 50

// Znajdź wszystkie wydarzenia
MATCH (e:Event)
RETURN e.name, e.date_start, e.location

// Znajdź prelegentów na wydarzeniu
MATCH (p:Person)-[:SPEAKER_AT]->(e:Event {name: "Spotkanie Rodzin Po Bratersku 2025"})
RETURN p.name

// Znajdź co opublikował profil
MATCH (profile:Profile)-[:PUBLISHED]->(post:Post)
RETURN profile.name, post.name, post.date_posted

// Znajdź organizacje i ich profile
MATCH (o:Organization)-[:HAS_PROFILE]->(p:Profile)
RETURN o.name, p.platform, p.url
```

## 📊 KROK 8: ANALIZA SIECI

### Dostępne analizy w Neo4j:

```cypher
// Najbardziej połączone osoby
MATCH (p:Person)-[r]->()
RETURN p.name, count(r) as connections
ORDER BY connections DESC
LIMIT 10

// Organizacje z największą liczbą wydarzeń
MATCH (o:Organization)-[:ORGANIZES]->(e:Event)
RETURN o.name, count(e) as events_count
ORDER BY events_count DESC

// Ścieżki między dwoma osobami
MATCH path = shortestPath(
  (p1:Person {name: "Jakub Kuśpit"})-[*]-(p2:Person {name: "Mieczysław Bielak"})
)
RETURN path

// Wykryj społeczności (wymaga APOC/GDS)
CALL gds.louvain.stream('myGraph')
YIELD nodeId, communityId
RETURN gds.util.asNode(nodeId).name AS name, communityId
ORDER BY communityId ASC
```

## ⚙️ KONFIGURACJA ŚRODOWISKA

### Credentials (.env):
```env
NEO4J_URI=neo4j+s://1f589f65.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=[twoje_haslo]
```

### Python packages (requirements.txt):
```txt
neo4j>=5.0.0
python-dotenv
streamlit
networkx
pyvis
duckdb
pandas
playwright
```

## 🚨 NAJCZĘSTSZE BŁĘDY I ROZWIĄZANIA

### Problem: "Relacje się nie ładują"
**Przyczyna:** Węzły nie mają wspólnej etykiety Entity (stary kod)
**Rozwiązanie:** Użyj `MATCH (source {id: $source_id})` zamiast `MATCH (source:Entity {id: $source_id})`

### Problem: "Wszystkie węzły mają ten sam kolor"
**Przyczyna:** Neo4j Explore koloruje po dominującej etykiecie
**Rozwiązanie:** Usuń etykietę Entity, zostaw tylko specyficzne (Organization, Person, Profile, Event, Post)

### Problem: "Duplikaty w bazie"
**Przyczyna:** Ten sam ID używany dla różnych encji
**Rozwiązanie:** Sprawdzaj unikalne ID przed dodaniem, używaj UUID dla postów

### Problem: "Brak połączenia z Neo4j Aura"
**Przyczyna:** Błędne credentials w .env
**Rozwiązanie:** Sprawdź URI (z `neo4j+s://`), user, password

## 📚 PLIKI ŹRÓDŁOWE DO SPRAWDZENIA

Jeśli potrzebujesz więcej kontekstu:

- **Definicje pól:** `schemas/FIELD_DEFINITIONS.md`
- **Prompt analizy:** `docs/LLM_ANALYSIS_PROMPT.md`
- **Schemat bazy:** `docs/DATABASE_SCHEMA.md`
- **Template organizacji:** `schemas/organization_template.json`
- **Template osoby:** `schemas/individual_template.json`
- **Przykładowy output:** `schemas/analysis_output.json`

## ✅ CHECKLIST DLA LLM

Przed zakończeniem analizy screenshotu sprawdź:

- [ ] Zidentyfikowano wszystkie osoby wymienione w tekście/obrazie
- [ ] Zidentyfikowano organizację/profil autora
- [ ] Utworzono node dla samego posta
- [ ] Jeśli post ogłasza wydarzenie - utworzono node Event
- [ ] Wszystkie ID są unikalne i zgodne z konwencją
- [ ] Wszystkie relacje mają `source_id` i `target_id`
- [ ] Confidence level jest uzasadniony
- [ ] Evidence zawiera źródło informacji
- [ ] JSON jest poprawnie sformatowany (valid JSON)
- [ ] Zapisano wynik analizy w `data/processed/graph_increments/`
- [ ] Wykonano migrację do Neo4j (`python scripts/load_to_neo4j.py`)
- [ ] Zweryfikowano dane w Neo4j Explore

---

## 🎯 PRZYKŁAD KOMPLETNEGO WORKFLOW

**Input użytkownika:**
> "Przeanalizuj ten screenshot - to post od Braterstwa Ludzi Wolnych o zlocie z 6 prelegentami"

**Twoje kroki:**

1. **Analiza obrazu:**
   - Rozpoznaję tekst na obrazie
   - Wyciągam nazwy: "Jakub Kuśpit", "Mieczysław Bielak", itd.
   - Rozpoznaję nazwę wydarzenia: "Spotkanie Rodzin Po Bratersku 2025"
   - Rozpoznaję autora: profil FB "Braterstwa Ludzi Wolnych"

2. **Tworzę entities (nodes):**
   ```json
   [
     {"id": "org-braterstwa-ludzi-wolnych", "entity_type": "organization", "name": "Braterstwa Ludzi Wolnych"},
     {"id": "profile-braterstwa-ludzi-wolnych", "entity_type": "profile", "name": "FB: Braterstwa Ludzi Wolnych"},
     {"id": "post-001", "entity_type": "post", "name": "Post: Harmonogram Spotkania"},
     {"id": "evt-001", "entity_type": "event", "name": "Spotkanie Rodzin Po Bratersku 2025"},
     {"id": "ent-002", "entity_type": "person", "name": "Jakub Kuśpit"},
     // ... 5 więcej osób
   ]
   ```

3. **Tworzę relationships (edges):**
   ```json
   [
     {"source_id": "org-braterstwa-ludzi-wolnych", "target_id": "profile-braterstwa-ludzi-wolnych", "relationship_type": "HAS_PROFILE"},
     {"source_id": "profile-braterstwa-ludzi-wolnych", "target_id": "post-001", "relationship_type": "PUBLISHED"},
     {"source_id": "post-001", "target_id": "evt-001", "relationship_type": "ANNOUNCES"},
     {"source_id": "org-braterstwa-ludzi-wolnych", "target_id": "evt-001", "relationship_type": "ORGANIZES"},
     {"source_id": "ent-002", "target_id": "evt-001", "relationship_type": "SPEAKER_AT"},
     // ... 5 więcej SPEAKER_AT
   ]
   ```

4. **Zapisuję do JSON:**
   - Zapisuję plik `data/processed/graph_increments/analysis_fb_BraterstwaLudziWolnych_123.json`
   - Struktura: `{"nodes": [...], "edges": [...]}`

5. **Migruję do Neo4j:**
   ```bash
   python scripts/load_to_neo4j.py
   ```

6. **Weryfikuję:**
   ```bash
   python scripts/check_neo4j_data.py
   ```
   Output: "10 węzłów, 10 relacji - OK"

7. **Informuję użytkownika:**
   > "Załadowano 10 węzłów (1 organizacja, 1 profil, 1 post, 1 wydarzenie, 6 osób) i 10 relacji do Neo4j Aura. Możesz teraz przeglądać graf w Neo4j Explore."

---

**KONIEC INSTRUKCJI**