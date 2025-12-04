# RUSSINT - Rozszerzony Schemat Bazy Danych
## Pełna analiza potrzeb systemu śledzenia dezinformacji

---

## 📊 ANALIZA OBECNEGO STANU

### Co już mamy:
- `entities` - podmioty (osoby, organizacje, strony)
- `posts` - posty z mediów społecznościowych
- `relationships` - relacje między podmiotami
- `narratives` - narracje/kampanie dezinformacyjne

### Czego brakuje (na podstawie analizy danych):

---

## 🆕 NOWE TABELE

### 1. `evidence` - Dowody (kluczowe dla OSINT!)
```sql
CREATE TABLE evidence (
    id              UUID PRIMARY KEY,
    evidence_type   VARCHAR(50) NOT NULL,           -- screenshot, article, video, document, audio, report
    title           VARCHAR(500),                   -- Tytuł/nazwa dowodu
    description     TEXT,                           -- Co pokazuje ten dowód
    
    -- Linki
    original_url    TEXT,                           -- Oryginalny URL
    archive_url     TEXT,                           -- archive.org / archive.today
    local_path      TEXT,                           -- Ścieżka do lokalnego pliku
    
    -- Metadane źródła
    source_platform VARCHAR(100),                   -- Twitter, Facebook, YouTube, artykuł
    source_author   VARCHAR(255),                   -- Autor źródła
    source_date     TIMESTAMP,                      -- Data publikacji źródła
    
    -- Weryfikacja
    verified        BOOLEAN DEFAULT FALSE,
    verification_date TIMESTAMP,
    verified_by     VARCHAR(255),                   -- Kto zweryfikował
    
    -- Kategoryzacja
    tags            JSONB,                          -- Tagi
    
    -- Powiązania
    related_entity_id UUID REFERENCES entities(id),
    related_post_id   UUID REFERENCES posts(id),
    related_narrative_id UUID REFERENCES narratives(id),
    
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    notes           TEXT
);
```

### 2. `external_links` - Linki zewnętrzne (trackowanie źródeł dezinformacji)
```sql
CREATE TABLE external_links (
    id              UUID PRIMARY KEY,
    url             TEXT NOT NULL,
    domain          VARCHAR(255),                   -- Wyekstrahowana domena
    title           VARCHAR(500),                   -- Tytuł strony
    
    -- Kategoryzacja domeny
    domain_category VARCHAR(100),                   -- news, blog, government, social, video, unknown
    domain_credibility VARCHAR(50),                 -- trusted, questionable, disinformation, unknown
    domain_country  VARCHAR(10),                    -- Kraj domeny
    
    -- Powiązania
    first_seen_in_post_id UUID REFERENCES posts(id),
    
    -- Statystyki
    times_shared    INTEGER DEFAULT 1,              -- Ile razy linkowano
    first_seen      TIMESTAMP,
    last_seen       TIMESTAMP,
    
    created_at      TIMESTAMP DEFAULT NOW(),
    notes           TEXT
);

-- Znane domeny dezinformacyjne
CREATE TABLE known_domains (
    domain          VARCHAR(255) PRIMARY KEY,
    credibility     VARCHAR(50),                    -- trusted, questionable, disinformation, state_media
    category        VARCHAR(100),                   -- Russian state media, alternative media, conspiracy
    country         VARCHAR(10),
    description     TEXT,
    added_at        TIMESTAMP DEFAULT NOW()
);
```

### 3. `media_files` - Pliki multimedialne (obrazy, video)
```sql
CREATE TABLE media_files (
    id              UUID PRIMARY KEY,
    media_type      VARCHAR(50) NOT NULL,           -- image, video, audio, document
    
    -- URLs
    original_url    TEXT,                           -- URL źródłowy
    local_path      TEXT,                           -- Ścieżka lokalna
    thumbnail_path  TEXT,                           -- Miniaturka
    
    -- Metadane
    file_hash       VARCHAR(64),                    -- SHA256 do deduplikacji
    file_size       BIGINT,
    mime_type       VARCHAR(100),
    width           INTEGER,
    height          INTEGER,
    duration        INTEGER,                        -- dla video/audio (sekundy)
    
    -- Analiza obrazu (future: AI)
    ocr_text        TEXT,                           -- Tekst z OCR
    detected_faces  INTEGER,
    detected_logos  JSONB,                          -- Wykryte loga
    
    -- Powiązania
    post_id         UUID REFERENCES posts(id),
    
    created_at      TIMESTAMP DEFAULT NOW()
);
```

### 4. `hashtags` - Hashtagi i ich tracking
```sql
CREATE TABLE hashtags (
    id              UUID PRIMARY KEY,
    tag             VARCHAR(255) NOT NULL UNIQUE,   -- bez #
    platform        VARCHAR(50),                    -- jeśli specyficzny dla platformy
    
    -- Statystyki
    total_uses      INTEGER DEFAULT 0,
    first_seen      TIMESTAMP,
    last_seen       TIMESTAMP,
    
    -- Klasyfikacja
    category        VARCHAR(100),                   -- political, disinformation, neutral, organic
    related_narrative_id UUID REFERENCES narratives(id),
    
    created_at      TIMESTAMP DEFAULT NOW()
);

-- Powiązanie M:M hashtag-post
CREATE TABLE post_hashtags (
    post_id         UUID REFERENCES posts(id),
    hashtag_id      UUID REFERENCES hashtags(id),
    PRIMARY KEY (post_id, hashtag_id)
);
```

### 5. `mentions` - Wzmianki o osobach/podmiotach
```sql
CREATE TABLE mentions (
    id              UUID PRIMARY KEY,
    post_id         UUID REFERENCES posts(id),
    mentioned_entity_id UUID REFERENCES entities(id),
    mentioned_handle VARCHAR(255),                  -- @handle jeśli nie mamy w entities
    mention_type    VARCHAR(50),                    -- tag, quote, reference
    context         TEXT,                           -- Fragment tekstu z wzmianką
    
    created_at      TIMESTAMP DEFAULT NOW()
);
```

### 6. `events` - Wydarzenia/Kampanie koordynowane
```sql
CREATE TABLE events (
    id              UUID PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    event_type      VARCHAR(100),                   -- protest, conference, online_campaign, coordinated_action
    description     TEXT,
    
    -- Czasowość
    start_date      TIMESTAMP,
    end_date        TIMESTAMP,
    
    -- Lokalizacja
    location        VARCHAR(255),
    location_coords POINT,                          -- lat/lng
    is_online       BOOLEAN DEFAULT FALSE,
    
    -- Powiązania
    organizer_id    UUID REFERENCES entities(id),
    related_narrative_id UUID REFERENCES narratives(id),
    
    -- Skala
    estimated_participants INTEGER,
    online_reach    INTEGER,                        -- zasięg online
    
    created_at      TIMESTAMP DEFAULT NOW(),
    notes           TEXT
);

-- Uczestnicy wydarzenia
CREATE TABLE event_participants (
    event_id        UUID REFERENCES events(id),
    entity_id       UUID REFERENCES entities(id),
    role            VARCHAR(100),                   -- organizer, speaker, participant, sponsor
    PRIMARY KEY (event_id, entity_id)
);
```

### 7. `funding` - Finansowanie (kluczowe dla OSINT!)
```sql
CREATE TABLE funding (
    id              UUID PRIMARY KEY,
    recipient_id    UUID REFERENCES entities(id),   -- Kto otrzymał
    source_id       UUID REFERENCES entities(id),   -- Od kogo (jeśli znane)
    source_name     VARCHAR(255),                   -- Nazwa jeśli nie ma w entities
    
    -- Szczegóły
    funding_type    VARCHAR(100),                   -- grant, donation, commercial, government, unknown
    amount          DECIMAL(15,2),
    currency        VARCHAR(10),
    
    -- Czasowość
    date_received   DATE,
    date_range_start DATE,
    date_range_end  DATE,
    is_recurring    BOOLEAN DEFAULT FALSE,
    
    -- Weryfikacja
    confidence      VARCHAR(50),                    -- confirmed, high, medium, low, suspected
    evidence_id     UUID REFERENCES evidence(id),
    
    created_at      TIMESTAMP DEFAULT NOW(),
    notes           TEXT
);
```

### 8. `coordinated_activity` - Skoordynowana aktywność (wykrywanie botów)
```sql
CREATE TABLE coordinated_activity (
    id              UUID PRIMARY KEY,
    detection_date  TIMESTAMP NOT NULL,
    activity_type   VARCHAR(100),                   -- mass_posting, synchronized_sharing, hashtag_hijack
    
    -- Szczegóły
    description     TEXT,
    involved_entities JSONB,                        -- Lista ID zaangażowanych podmiotów
    post_ids        JSONB,                          -- Lista ID postów
    
    -- Metryki
    time_window_minutes INTEGER,                    -- Okno czasowe
    entity_count    INTEGER,                        -- Ile podmiotów
    post_count      INTEGER,                        -- Ile postów
    similarity_score DECIMAL(3,2),                  -- Podobieństwo treści
    
    -- Klasyfikacja
    confidence      VARCHAR(50),                    -- certain, high, medium, low
    is_confirmed    BOOLEAN DEFAULT FALSE,
    
    created_at      TIMESTAMP DEFAULT NOW(),
    notes           TEXT
);
```

### 9. `analyst_reports` - Raporty analityka
```sql
CREATE TABLE analyst_reports (
    id              UUID PRIMARY KEY,
    title           VARCHAR(500) NOT NULL,
    report_type     VARCHAR(100),                   -- entity_profile, narrative_analysis, network_map, incident_report
    
    -- Treść
    summary         TEXT,
    full_content    TEXT,
    
    -- Powiązania
    related_entities JSONB,                         -- Lista ID podmiotów
    related_narratives JSONB,                       -- Lista ID narracji
    related_posts   JSONB,                          -- Lista ID postów
    
    -- Metadane
    author          VARCHAR(255),
    status          VARCHAR(50),                    -- draft, review, published, archived
    classification  VARCHAR(50),                    -- public, internal, restricted
    
    created_at      TIMESTAMP DEFAULT NOW(),
    updated_at      TIMESTAMP DEFAULT NOW(),
    published_at    TIMESTAMP
);
```

### 10. `aliases` - Aliasy i alternatywne nazwy
```sql
CREATE TABLE aliases (
    id              UUID PRIMARY KEY,
    entity_id       UUID REFERENCES entities(id),
    alias           VARCHAR(255) NOT NULL,
    alias_type      VARCHAR(50),                    -- nickname, former_name, translation, handle
    platform        VARCHAR(50),                    -- jeśli specyficzny dla platformy
    is_primary      BOOLEAN DEFAULT FALSE,
    
    created_at      TIMESTAMP DEFAULT NOW()
);
```

---

## 🔄 ROZSZERZENIA ISTNIEJĄCYCH TABEL

### Rozszerzenie `entities`:
```sql
ALTER TABLE entities ADD COLUMN IF NOT EXISTS:
    -- Geolokalizacja
    country         VARCHAR(100),                   -- Kraj działania
    region          VARCHAR(255),                   -- Region/województwo
    city            VARCHAR(255),                   -- Miasto
    
    -- Kontakt
    email           VARCHAR(255),
    phone           VARCHAR(50),
    website         TEXT,
    
    -- Status prawny (dla organizacji)
    legal_form      VARCHAR(100),                   -- fundacja, stowarzyszenie, spółka
    registration_number VARCHAR(100),               -- KRS, NIP
    registration_date DATE,
    
    -- Skala działania
    followers_count INTEGER,
    following_count INTEGER,
    posts_count     INTEGER,
    
    -- Weryfikacja
    is_verified_platform BOOLEAN DEFAULT FALSE,     -- Czy zweryfikowany na platformie
    is_verified_analyst BOOLEAN DEFAULT FALSE,      -- Czy zweryfikowany przez analityka
    
    -- Klasyfikacja rozszerzona
    affiliation     VARCHAR(255),                   -- Powiązania polityczne/ideologiczne
    primary_language VARCHAR(10),
    secondary_languages JSONB,
    
    -- Aktywność
    activity_level  VARCHAR(50),                    -- very_active, active, moderate, inactive, dormant
    last_post_date  TIMESTAMP,
    
    -- Profil dezinformacyjny
    disinformation_score INTEGER CHECK (disinformation_score BETWEEN 0 AND 100),
    primary_narratives JSONB                        -- Lista głównych narracji
;
```

### Rozszerzenie `posts`:
```sql
ALTER TABLE posts ADD COLUMN IF NOT EXISTS:
    -- Treść rozszerzona
    title           VARCHAR(500),                   -- Tytuł (dla artykułów, video)
    language        VARCHAR(10),                    -- Język posta
    
    -- Engagement rozszerzony
    reactions       JSONB,                          -- {like: 10, love: 5, angry: 3...}
    views_count     INTEGER,
    
    -- Status moderacji
    is_deleted      BOOLEAN DEFAULT FALSE,
    deleted_at      TIMESTAMP,
    deletion_reason VARCHAR(255),
    
    -- Analiza treści
    contains_misinfo BOOLEAN,                       -- Zawiera dezinformację?
    fact_check_status VARCHAR(50),                  -- unchecked, false, misleading, true, partly_true
    fact_check_url  TEXT,                           -- Link do fact-checku
    
    -- Koordynacja
    is_coordinated  BOOLEAN DEFAULT FALSE,          -- Część skoordynowanej kampanii?
    coordination_id UUID REFERENCES coordinated_activity(id),
    
    -- Viralność
    reach_estimate  INTEGER,                        -- Szacowany zasięg
    virality_score  DECIMAL(5,2)                    -- Współczynnik wiralności
;
```

### Rozszerzenie `narratives`:
```sql
ALTER TABLE narratives ADD COLUMN IF NOT EXISTS:
    -- Klasyfikacja rozszerzona
    origin_country  VARCHAR(100),                   -- Kraj pochodzenia narracji
    target_countries JSONB,                         -- Lista krajów docelowych
    target_groups   JSONB,                          -- Grupy docelowe
    
    -- Techniki
    techniques      JSONB,                          -- Lista technik dezinformacyjnych
    -- np: ["emotional_appeal", "false_context", "fabricated_content", "misleading_headline"]
    
    -- Źródła
    known_sources   JSONB,                          -- Lista znanych źródeł narracji
    primary_spreaders JSONB,                        -- Główni rozpowszechniający
    
    -- Metryki
    estimated_reach INTEGER,                        -- Szacowany zasięg
    posts_count     INTEGER,                        -- Ile postów z tą narracją
    entities_count  INTEGER,                        -- Ile podmiotów rozpowszechnia
    
    -- Cykl życia
    lifecycle_stage VARCHAR(50),                    -- emerging, growing, peak, declining, dormant
    
    -- Fact-checking
    debunked        BOOLEAN DEFAULT FALSE,
    debunk_urls     JSONB                           -- Linki do obalenia
;
```

---

## 📈 WIDOKI ANALITYCZNE

### Sieć wpływów
```sql
CREATE VIEW influence_network AS
SELECT 
    e.name,
    e.entity_type,
    e.threat_level,
    COUNT(DISTINCT p.id) as posts_count,
    COUNT(DISTINCT CASE WHEN p.is_repost THEN p.id END) as reposts_count,
    COUNT(DISTINCT m.mentioned_entity_id) as entities_mentioned,
    AVG(p.likes_count) as avg_engagement
FROM entities e
LEFT JOIN posts p ON e.id = p.author_id
LEFT JOIN mentions m ON p.id = m.post_id
GROUP BY e.id;
```

### Tracking narracji w czasie
```sql
CREATE VIEW narrative_timeline AS
SELECT 
    n.name as narrative,
    DATE_TRUNC('week', p.date_posted) as week,
    COUNT(*) as post_count,
    COUNT(DISTINCT p.author_id) as unique_authors,
    SUM(p.likes_count + p.shares_count) as total_engagement
FROM narratives n
JOIN posts p ON p.narrative_id = n.id
GROUP BY n.id, n.name, DATE_TRUNC('week', p.date_posted)
ORDER BY week DESC;
```

### Analiza koordynacji
```sql
CREATE VIEW coordination_analysis AS
SELECT 
    DATE_TRUNC('hour', p.date_posted) as hour,
    p.text_hash,                                    -- Hash treści do wykrycia duplikatów
    COUNT(*) as duplicate_count,
    COUNT(DISTINCT p.author_id) as authors_count,
    ARRAY_AGG(DISTINCT e.name) as authors
FROM posts p
JOIN entities e ON p.author_id = e.id
GROUP BY hour, p.text_hash
HAVING COUNT(*) > 2                                 -- Podejrzana aktywność = >2 takie same posty
ORDER BY hour DESC;
```

---

## 🔗 PEŁNY DIAGRAM RELACJI

```
                                    ┌─────────────────┐
                                    │   narratives    │
                                    └────────┬────────┘
                                             │
           ┌─────────────────────────────────┼─────────────────────────────────┐
           │                                 │                                 │
           ▼                                 ▼                                 ▼
    ┌──────────────┐              ┌─────────────────┐              ┌──────────────────┐
    │   events     │              │     posts       │              │ coordinated_act  │
    └──────┬───────┘              └────────┬────────┘              └──────────────────┘
           │                               │
           │                    ┌──────────┼──────────┐
           │                    │          │          │
           ▼                    ▼          ▼          ▼
    ┌─────────────────┐  ┌──────────┐ ┌─────────┐ ┌──────────────┐
    │ event_particip  │  │ mentions │ │ hashtags│ │ media_files  │
    └────────┬────────┘  └──────────┘ └─────────┘ └──────────────┘
             │                                
             ▼                                
    ┌─────────────────┐        ┌─────────────────┐
    │    entities     │◄───────│   aliases       │
    └────────┬────────┘        └─────────────────┘
             │
    ┌────────┼────────┬────────────────┐
    │        │        │                │
    ▼        ▼        ▼                ▼
┌────────┐ ┌────────┐ ┌─────────────┐ ┌────────────────┐
│funding │ │evidence│ │relationships│ │external_links  │
└────────┘ └────────┘ └─────────────┘ └────────────────┘
                                              │
                                              ▼
                                     ┌────────────────┐
                                     │ known_domains  │
                                     └────────────────┘
```

---

## 📋 PRIORYTETYZACJA IMPLEMENTACJI

### 🔴 Krytyczne (Phase 1):
1. **`evidence`** - bez dowodów analiza OSINT jest niekompletna
2. **`external_links` + `known_domains`** - trackowanie źródeł dezinformacji
3. **`aliases`** - podmioty często zmieniają nazwy/handle
4. **`hashtags`** - kluczowe do trackowania kampanii

### 🟡 Ważne (Phase 2):
5. **`media_files`** - archiwizacja obrazów/video
6. **`mentions`** - sieć wzmianek
7. **`funding`** - follow the money

### 🟢 Rozszerzenia (Phase 3):
8. **`events`** - koordynowane wydarzenia
9. **`coordinated_activity`** - wykrywanie botów
10. **`analyst_reports`** - dokumentacja analiz

---

## 🛠️ INDEKSY WYDAJNOŚCIOWE

```sql
-- Wyszukiwanie po tekście
CREATE INDEX idx_posts_text_gin ON posts USING gin(to_tsvector('simple', text));

-- Wyszukiwanie po datach
CREATE INDEX idx_posts_date ON posts(date_posted DESC);
CREATE INDEX idx_entities_last_activity ON entities(last_activity DESC);

-- Wyszukiwanie po platformie
CREATE INDEX idx_posts_platform ON posts(platform);
CREATE INDEX idx_entities_platform ON entities(platform);

-- Wyszukiwanie po klasyfikacji
CREATE INDEX idx_entities_threat ON entities(threat_level);
CREATE INDEX idx_posts_narrative ON posts(narrative_id);

-- Wyszukiwanie po domenach
CREATE INDEX idx_external_links_domain ON external_links(domain);
```

---

## 📊 PRZYKŁADOWE ZAPYTANIA ANALITYCZNE

### Top 10 podmiotów rozpowszechniających dezinformację
```sql
SELECT e.name, e.platform, e.threat_level,
       COUNT(p.id) as total_posts,
       COUNT(CASE WHEN p.contains_misinfo THEN 1 END) as misinfo_posts
FROM entities e
JOIN posts p ON e.id = p.author_id
GROUP BY e.id
ORDER BY misinfo_posts DESC
LIMIT 10;
```

### Narracje z ostatniego tygodnia
```sql
SELECT n.name, COUNT(p.id) as posts,
       COUNT(DISTINCT p.author_id) as unique_spreaders
FROM narratives n
JOIN posts p ON p.narrative_id = n.id
WHERE p.date_posted > NOW() - INTERVAL '7 days'
GROUP BY n.id
ORDER BY posts DESC;
```

### Domeny najczęściej linkowane przez podmioty high-risk
```sql
SELECT el.domain, el.domain_credibility, COUNT(*) as times_linked
FROM external_links el
JOIN posts p ON el.first_seen_in_post_id = p.id
JOIN entities e ON p.author_id = e.id
WHERE e.threat_level IN ('high', 'critical')
GROUP BY el.domain, el.domain_credibility
ORDER BY times_linked DESC
LIMIT 20;
```
