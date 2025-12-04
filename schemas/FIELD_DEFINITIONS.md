# Definicje Pól JSON - Przewodnik dla LLM

## ORGANIZACJA (organization_template.json)

### Podstawowe Informacje
- **`id`**: Unikalny identyfikator w formacie `org-nazwa-skrot` (np. `org-fundacja-promowanie-pokoju`)
- **`entity_type`**: Zawsze `"organization"`
- **`name`**: Pełna oficjalna nazwa organizacji
- **`aliases`**: Lista alternatywnych nazw, skrótów, nazw potocznych
- **`description`**: Krótki opis (2-4 zdania) działalności i profilu dezinformacyjnego
- **`country_of_origin`**: Kraj rejestracji (ISO 3166-1 alpha-2, np. "PL", "RU")
- **`legal_status`**: np. "fundacja", "stowarzyszenie", "spółka z o.o.", "niezarejestrowana"
- **`registration_number`**: NIP, KRS, REGON (jeśli dostępne)
- **`headquarters_address`**: Adres siedziby
- **`status`**: `"active"` / `"inactive"` / `"dissolved"` / `"suspended"`
- **`risk_level`**: `"critical"` / `"high"` / `"medium"` / `"low"` / `"monitoring"`

### Leadership (Kierownictwo)
Osoby w kluczowych rolach zarządczych:
- **`role`**: np. "Prezes", "Dyrektor", "Założyciel", "Członek Zarządu"
- **`name`**: Imię i nazwisko
- **`person_id`**: ID z osobnego pliku JSON tej osoby (jeśli istnieje), format: `person-imie-nazwisko`

### Key Members
Lista innych istotnych osób związanych z organizacją (format jak `leadership`)

### Online Presence
Wszystkie profile społecznościowe i strony:
- **`platform`**: "Facebook", "Twitter/X", "Telegram", "VKontakte", "YouTube", "Website", "TikTok"
- **`url`**: Pełny link
- **`handle`**: Nazwa użytkownika (np. "@nazwa")
- **`status`**: `"active"` / `"banned"` / `"deleted"` / `"suspended"` / `"archived"`
- **`followers_count`**: Liczba obserwujących (jeśli znana)
- **`archive_url`**: Link do Wayback Machine lub archive.today
- **`last_checked`**: Data ostatniego sprawdzenia (format: "YYYY-MM-DD")

### Contact Info
- **`email`**: Adres email (może być pusty string)
- **`phone`**: Numer telefonu z kierunkowym (np. "+48 123 456 789")
- **`website`**: Główna strona WWW

### Narratives (Narracje)
Lista propagowanych narracji. Przykłady:
- "anty-NATO"
- "negowanie zbrodni wojennych rosyjskich"
- "Ukraina jako państwo sztuczne"
- "teoria o bio-laboratoriach USA"
- "anty-UE"
- "anty-zachodnie"
- "pro-kremlowskie"
- "teoria spisku o Majdanie"

### Tags
Dodatkowe etykiety kategoryzujące: np. "dezinformacja", "propaganda", "think tank", "media", "aktywizm", "finansowanie rosyjskie"

### Funding Sources (Źródła Finansowania)
- **`source_name`**: Nazwa źródła finansowania
- **`source_id`**: ID podmiotu finansującego (jeśli jest w bazie)
- **`type`**: "grant", "donation", "commercial", "government", "unknown"
- **`amount`**: Kwota (liczba)
- **`currency`**: "PLN", "USD", "EUR", "RUB"
- **`date`**: Data otrzymania środków
- **`evidence`**: Krótki opis dowodu lub ID dowodu z sekcji `evidence`

### Connections (Powiązania)
Relacje z innymi podmiotami:
- **`entity_id`**: ID powiązanej organizacji/osoby
- **`entity_name`**: Nazwa dla czytelności
- **`relationship_type`**: 
  - "partner" (współpraca)
  - "founder" (założyciel)
  - "funder" (finansujący)
  - "member" (członek)
  - "subsidiary" (podmiot zależny)
  - "parent_organization" (organizacja nadrzędna)
  - "affiliate" (afiliacja)
- **`description`**: Opis relacji
- **`confidence_level`**: `"confirmed"` / `"high"` / `"medium"` / `"low"` / `"suspected"`
- **`date_established`**: Kiedy nawiązano relację

### Activities (Działania)
Chronologia istotnych działań:
- **`date`**: Data wydarzenia
- **`type`**: "conference", "publication", "protest", "campaign", "event", "statement"
- **`description`**: Opis działania
- **`impact`**: Ocena wpływu (np. "10k wyświetleń", "szeroko nagłośnione")
- **`evidence_id`**: ID dowodu z sekcji evidence

### Evidence (Dowody)
- **`id`**: Unikalny ID dowodu (np. "ev-001")
- **`type`**: "screenshot", "article", "video", "document", "audio", "report", "photo"
- **`url`**: Link źródłowy (jeśli istnieje)
- **`archive_url`**: Link do archiwum
- **`path`**: Ścieżka do pliku lokalnego (np. "data/evidence/screenshot_001.png")
- **`title`**: Tytuł/nazwa dowodu
- **`description`**: Co pokazuje ten dowód
- **`date`**: Data powstania/publikacji materiału
- **`source`**: Skąd pochodzi (np. "Twitter", "własne zrzuty")
- **`tags`**: Tagi do kategoryzacji

### Metadata
- **`created_at`**: Data utworzenia wpisu (ISO 8601: "YYYY-MM-DDTHH:MM:SSZ")
- **`updated_at`**: Data ostatniej aktualizacji
- **`created_by`**: Kto stworzył wpis (np. "Jan Kowalski", "LLM")
- **`source`**: "manual", "automated", "LLM-assisted"
- **`confidence_level`**: `"verified"` / `"high"` / `"medium"` / `"low"` / `"unverified"`
- **`verification_status`**: `"verified"` / `"pending"` / `"disputed"`
- **`notes`**: Dodatkowe uwagi

---

## OSOBA (individual_template.json)

### Podstawowe Informacje
- **`id`**: Format `person-imie-nazwisko` (np. `person-jan-kowalski`)
- **`entity_type`**: Zawsze `"individual"`
- **`full_name`**: Pełne imię i nazwisko
- **`aliases`**: Pseudonimy, przezwiska, inne wersje nazwiska
- **`date_of_birth`**: Format "YYYY-MM-DD" (lub "YYYY" jeśli znany tylko rok)
- **`place_of_birth`**: Miejsce urodzenia
- **`nationality`**: Lista obywatelstw (może być więcej niż jedno)
- **`current_residence`**: Obecne miejsce zamieszkania
- **`occupation`**: Lista zawodów/ról (np. ["dziennikarz", "aktywista"])
- **`education`**: Lista wykształcenia (np. ["Uniwersytet Warszawski, Dziennikarstwo, 2010"])
- **`languages`**: Języki, którymi posługuje się osoba
- **`status`**: `"active"` / `"inactive"` / `"deceased"` / `"imprisoned"`
- **`risk_level`**: `"critical"` / `"high"` / `"medium"` / `"low"` / `"monitoring"`

### Biography
Krótka biografia (3-5 zdań) z naciskiem na działalność dezinformacyjną.

### Online Presence
(Tak samo jak w organizacji, z dodatkiem pola `verified` - czy profil jest zweryfikowany)

### Affiliations (Przynależności)
Organizacje, z którymi jest/była związana osoba:
- **`organization_id`**: ID organizacji
- **`organization_name`**: Nazwa organizacji
- **`role`**: Rola w organizacji
- **`start_date`**: Data rozpoczęcia
- **`end_date`**: Data zakończenia (null jeśli nadal trwa)
- **`status`**: `"current"` / `"former"`

### Narratives, Tags, Connections
(Analogicznie jak w organizacji)

### Activities
(Jak w organizacji, z dodatkiem pola `platform` - na jakiej platformie było działanie)

### Media Appearances (Wystąpienia Medialne)
- **`date`**: Data wystąpienia
- **`outlet`**: Nazwa medium (np. "TVP Info", "Radio Maryja")
- **`type`**: "interview", "article", "opinion", "debate", "podcast"
- **`title`**: Tytuł materiału
- **`url`**: Link
- **`archive_url`**: Archiwum
- **`description`**: Krótki opis treści

### Income Sources (Źródła Dochodu)
- **`source_name`**: Nazwa źródła (np. "Portal X", "Fundacja Y")
- **`type`**: "employment", "contract", "grant", "sponsorship", "unknown"
- **`description`**: Opis
- **`date`**: Data/okres

### Legal Issues (Sprawy Prawne)
- **`date`**: Data
- **`type`**: "criminal", "civil", "administrative", "investigation"
- **`description`**: Opis sprawy
- **`status`**: "ongoing", "closed", "appealed"
- **`outcome`**: Wynik (jeśli sprawa zamknięta)

### Evidence, Metadata
(Tak samo jak w organizacji)

---

## INSTRUKCJE DLA LLM

Gdy otrzymasz informacje o organizacji lub osobie:

1. **Wybierz odpowiedni szablon** (organization lub individual)
2. **Wygeneruj ID**: 
   - Dla organizacji: `org-` + nazwa-małymi-literami-bez-polskich-znaków-z-myślnikami
   - Dla osób: `person-` + imie-nazwisko-małymi-literami-bez-polskich-znaków
3. **Wypełnij wszystkie znane pola**. Jeśli nie masz informacji:
   - Dla string: użyj `""`
   - Dla liczb: użyj `null`
   - Dla tablic: użyj `[]`
   - Dla obiektów: użyj `null` lub pozostaw pusty obiekt `{}`
4. **Risk Level** określ na podstawie:
   - `critical`: Bezpośrednie powiązania z rosyjskimi służbami, aktywne prowadzenie kampanii dezinformacyjnych
   - `high`: Regularne promowanie narracji pro-kremlowskich, udokumentowane powiązania finansowe
   - `medium`: Sporadyczne powielanie narracji, brak bezpośrednich dowodów powiązań
   - `low`: Pojedyncze przypadki problematycznych treści
   - `monitoring`: Wymagające obserwacji, ale bez wyraźnych oznak
5. **Confidence Level** w powiązaniach:
   - `confirmed`: Udokumentowane oficjalnymi źródłami
   - `high`: Bardzo wiarygodne źródła, multiple sources
   - `medium`: Pojedyncze wiarygodne źródło
   - `low`: Nieoficjalne źródła, doniesienia
   - `suspected`: Hipoteza oparta na poszlakach
6. **Zawsze wypełniaj metadata**: Ustaw `created_at` na aktualną datę, `created_by` na "LLM", `source` na "LLM-assisted"
7. **Narratives**: Używaj konkretnych, opisowych fraz, nie ogólników
8. **Evidence**: Dla każdego URL, **zawsze** dodaj `archive_url` (suggest using web.archive.org format)

## PRZYKŁAD DOBREGO UZUPEŁNIENIA

```json
{
  "id": "org-stop-operacji-nato",
  "entity_type": "organization",
  "name": "Komitet Stop Operacjom NATO",
  "aliases": ["KSON", "Stop NATO"],
  "description": "Organizacja pozarządowa rzekomo działająca na rzecz pokoju, w praktyce promująca narracje pro-kremlowskie i anty-NATO. Aktywna od 2022 roku.",
  "country_of_origin": "PL",
  "risk_level": "high",
  "leadership": [
    {
      "role": "Prezes",
      "name": "Jan Kowalski",
      "person_id": "person-jan-kowalski"
    }
  ],
  "online_presence": [
    {
      "platform": "Facebook",
      "url": "https://facebook.com/stopnato",
      "handle": "@stopnato",
      "status": "active",
      "followers_count": 45000,
      "archive_url": "https://web.archive.org/web/20251120/facebook.com/stopnato",
      "last_checked": "2025-11-24"
    }
  ],
  "narratives": [
    "NATO jako agresor",
    "Polska jako marionetka USA",
    "negowanie zagrożenia rosyjskiego"
  ],
  "metadata": {
    "created_at": "2025-11-24T12:00:00Z",
    "updated_at": "2025-11-24T12:00:00Z",
    "created_by": "LLM",
    "source": "LLM-assisted",
    "confidence_level": "high",
    "verification_status": "pending"
  }
}
```
