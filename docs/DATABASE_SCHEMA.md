# RUSSINT - Schemat Bazy Danych
## Analiza relacji i sieci dezinformacji

### Cel systemu
System ma umożliwiać:
1. Zbieranie danych o postach z mediów społecznościowych
2. Mapowanie relacji między podmiotami (osoby, organizacje, strony)
3. Analizę sieci dezinformacji (kto udostępnia czyje treści)
4. Śledzenie narracji i tematów

---

## ENCJE (Entities)

### 1. `entities` - Podmioty (osoby, organizacje, strony)
```sql
CREATE TABLE entities (
    id              UUID PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,          -- Nazwa wyświetlana
    handle          VARCHAR(255),                   -- @handle lub slug
    platform        VARCHAR(50) NOT NULL,           -- facebook, telegram, twitter, vk
    platform_id     VARCHAR(255),                   -- ID na platformie (jeśli znane)
    entity_type     VARCHAR(50),                    -- person, organization, page, group, channel
    url             TEXT,                           -- Link do profilu
    description     TEXT,                           -- Opis/bio
    followers_count INTEGER,                        -- Liczba obserwujących
    verified        BOOLEAN DEFAULT FALSE,          -- Czy zweryfikowany
    
    -- Klasyfikacja OSINT
    category        VARCHAR(100),                   -- np. "pro-kremlin", "alternative_media", "political"
    threat_level    VARCHAR(20),                    -- low, medium, high, critical
    country         VARCHAR(100),                   -- Kraj pochodzenia/działania
    language        VARCHAR(10),                    -- Główny język
    
    -- Metadane
    first_seen      TIMESTAMP,                      -- Kiedy pierwszy raz zauważony
    last_activity   TIMESTAMP,                      -- Ostatnia aktywność
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    notes           TEXT                            -- Notatki analityka
);
```

### 2. `posts` - Posty/Treści
```sql
CREATE TABLE posts (
    id              UUID PRIMARY KEY,
    platform        VARCHAR(50) NOT NULL,           -- facebook, telegram, etc.
    platform_post_id VARCHAR(255),                  -- ID posta na platformie
    url             TEXT,                           -- Link do posta
    
    -- Autorstwo
    author_id       UUID REFERENCES entities(id),   -- Kto opublikował
    
    -- Treść
    text            TEXT,                           -- Treść posta
    date_posted     TIMESTAMP,                      -- Data publikacji
    date_text       VARCHAR(100),                   -- Oryginalna data tekstowo ("3 tyg.")
    
    -- Repost/Udostępnienie
    is_repost       BOOLEAN DEFAULT FALSE,          -- Czy to repost?
    original_author_id UUID REFERENCES entities(id),-- Autor oryginalnego posta
    original_post_id UUID REFERENCES posts(id),     -- Oryginalny post (jeśli w bazie)
    original_url    TEXT,                           -- URL oryginalnego posta
    
    -- Linki zewnętrzne
    external_url    TEXT,                           -- Link w treści (artykuł, video)
    external_domain VARCHAR(255),                   -- Domena linku
    
    -- Media
    images          JSONB,                          -- Lista URL zdjęć
    videos          JSONB,                          -- Lista URL video
    
    -- Engagement (jeśli dostępne)
    likes_count     INTEGER,
    shares_count    INTEGER,
    comments_count  INTEGER,
    
    -- Klasyfikacja
    topics          JSONB,                          -- Tematy/tagi
    sentiment       VARCHAR(20),                    -- positive, negative, neutral
    narrative_id    UUID REFERENCES narratives(id), -- Powiązana narracja
    
    -- Metadane
    collected_at    TIMESTAMP DEFAULT NOW(),        -- Kiedy zebrano
    collection_method VARCHAR(50),                  -- manual, scraper, api
    verified        BOOLEAN DEFAULT FALSE,          -- Czy zweryfikowane przez analityka
    notes           TEXT,
    
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW()
);
```

### 3. `relationships` - Relacje między podmiotami
```sql
CREATE TABLE relationships (
    id              UUID PRIMARY KEY,
    source_id       UUID REFERENCES entities(id),   -- Podmiot źródłowy
    target_id       UUID REFERENCES entities(id),   -- Podmiot docelowy
    
    relationship_type VARCHAR(100) NOT NULL,        -- Typ relacji (patrz niżej)
    
    -- Szczegóły
    strength        INTEGER CHECK (strength BETWEEN 1 AND 10), -- Siła relacji
    direction       VARCHAR(20) DEFAULT 'directed', -- directed, bidirectional
    confidence      DECIMAL(3,2),                   -- Pewność (0.00-1.00)
    
    -- Dowody
    evidence_count  INTEGER DEFAULT 0,              -- Ile razy zaobserwowano
    first_observed  TIMESTAMP,
    last_observed   TIMESTAMP,
    
    -- Metadane
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(source_id, target_id, relationship_type)
);

-- Typy relacji:
-- SHARES_CONTENT_FROM  - udostępnia treści od
-- REPOSTS              - repostuje
-- MENTIONS             - wspomina
-- FOLLOWS              - obserwuje
-- COLLABORATES_WITH    - współpracuje z
-- MEMBER_OF            - członek organizacji
-- WORKS_FOR            - pracuje dla
-- FUNDED_BY            - finansowany przez
-- AMPLIFIES            - wzmacnia przekaz
-- SIMILAR_NARRATIVE    - podobna narracja
```

### 4. `narratives` - Narracje/Kampanie
```sql
CREATE TABLE narratives (
    id              UUID PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,          -- Nazwa narracji
    description     TEXT,                           -- Opis
    
    -- Klasyfikacja
    narrative_type  VARCHAR(100),                   -- disinformation, propaganda, conspiracy
    origin          VARCHAR(255),                   -- Przypuszczalne źródło
    target_audience VARCHAR(255),                   -- Docelowa grupa
    
    -- Czasowość
    first_seen      TIMESTAMP,
    peak_activity   TIMESTAMP,
    last_seen       TIMESTAMP,
    is_active       BOOLEAN DEFAULT TRUE,
    
    -- Powiązania
    keywords        JSONB,                          -- Słowa kluczowe
    hashtags        JSONB,                          -- Hashtagi
    
    -- Metadane
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    notes           TEXT
);
```

### 5. `interactions` - Szczegółowe interakcje (opcjonalne)
```sql
CREATE TABLE interactions (
    id              UUID PRIMARY KEY,
    post_id         UUID REFERENCES posts(id),
    entity_id       UUID REFERENCES entities(id),
    
    interaction_type VARCHAR(50),                   -- like, share, comment, repost
    timestamp       TIMESTAMP,
    
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

## WIDOKI (Views) dla analizy

### Sieć udostępnień
```sql
CREATE VIEW sharing_network AS
SELECT 
    e1.name as sharer,
    e2.name as original_author,
    COUNT(*) as share_count,
    MIN(p.date_posted) as first_share,
    MAX(p.date_posted) as last_share
FROM posts p
JOIN entities e1 ON p.author_id = e1.id
JOIN entities e2 ON p.original_author_id = e2.id
WHERE p.is_repost = TRUE
GROUP BY e1.id, e2.id, e1.name, e2.name;
```

### Aktywność podmiotów
```sql
CREATE VIEW entity_activity AS
SELECT 
    e.id,
    e.name,
    e.entity_type,
    COUNT(p.id) as post_count,
    COUNT(CASE WHEN p.is_repost THEN 1 END) as repost_count,
    COUNT(DISTINCT p.original_author_id) as sources_count
FROM entities e
LEFT JOIN posts p ON e.id = p.author_id
GROUP BY e.id, e.name, e.entity_type;
```

---

## DIAGRAM RELACJI (ERD)

```
┌─────────────┐         ┌─────────────┐
│  ENTITIES   │◄────────│    POSTS    │
│─────────────│ author  │─────────────│
│ id          │         │ id          │
│ name        │◄────────│ author_id   │
│ handle      │ original│ original_   │
│ platform    │ author  │ author_id   │
│ entity_type │         │ text        │
│ category    │         │ is_repost   │
│ threat_level│         │ narrative_id│
└──────┬──────┘         └──────┬──────┘
       │                       │
       │                       │
       ▼                       ▼
┌─────────────┐         ┌─────────────┐
│RELATIONSHIPS│         │ NARRATIVES  │
│─────────────│         │─────────────│
│ source_id   │         │ id          │
│ target_id   │         │ name        │
│ type        │         │ description │
│ strength    │         │ keywords    │
└─────────────┘         └─────────────┘
```

---

## Eksport do NetworkX / Gephi

```python
# Eksport sieci do analizy grafowej
def export_network(posts, entities):
    nodes = []
    edges = []
    
    for entity in entities:
        nodes.append({
            'id': entity['id'],
            'label': entity['name'],
            'type': entity['entity_type'],
            'category': entity['category']
        })
    
    for post in posts:
        if post['is_repost'] and post['original_author_id']:
            edges.append({
                'source': post['author_id'],
                'target': post['original_author_id'],
                'type': 'REPOSTS',
                'weight': 1
            })
    
    return {'nodes': nodes, 'edges': edges}
```
