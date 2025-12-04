# 🌐 RUSSINT - Neo4j Aura Setup (Darmowa instancja online)

## ✅ Masz już instancję!

**Twoja instancja:**
- ID: `1f589f65`
- URI: `neo4j+s://1f589f65.databases.neo4j.io`
- Typ: AuraDB Free
- Console: https://console-preview.neo4j.io/

## 1. Znajdź hasło

1. Wejdź na: https://console-preview.neo4j.io/
2. Zaloguj się
3. Wybierz projekt / instancję
4. Jeśli pierwsza instalacja - **zapisz hasło** (pokazuje się tylko raz!)
5. Jeśli zapomniałeś hasła:
   - Kliknij na instancję → **Reset password**
   - Zapisz nowe hasło

## 2. Ustaw hasło w PowerShell

```powershell
# Ustaw zmienną środowiskową (ważna tylko w tej sesji)
$env:NEO4J_PASSWORD = "twoje_haslo_z_neo4j_aura"

# Sprawdź
echo $env:NEO4J_PASSWORD
```

## 3. Załaduj dane

```powershell
# Uruchom migrację
python scripts/load_to_neo4j.py
```

Zobaczysz:
```
🔗 Łączę z: neo4j+s://1f589f65.databases.neo4j.io
👤 Użytkownik: neo4j
🗑️ Wyczyszczono bazę Neo4j
✅ Utworzono ograniczenia
✅ Załadowano 10 węzłów
✅ Załadowano 10 relacji
```

## 4. Otwórz Neo4j Browser

Neo4j Aura ma wbudowany Workspace:

1. Wejdź na: https://console-preview.neo4j.io/
2. Kliknij: **Open** przy swojej instancji
3. Lub: **Query** → otworzy się edytor Cypher
4. Wpisz zapytanie:
   ```cypher
   MATCH (n)-[r]->(m) 
   RETURN n, r, m 
   LIMIT 25
   ```
5. Kliknij **Run** (▶)

## 5. Uruchom aplikację Streamlit

```powershell
# Upewnij się że hasło jest ustawione
$env:NEO4J_PASSWORD = "twoje_haslo"

# Uruchom aplikację
streamlit run src/ui/neo4j_editor_app.py
```

Otwórz: http://localhost:8501

## Zalety Neo4j Aura vs lokalna instalacja

| Feature | Lokalny Neo4j | Neo4j Aura |
|---------|---------------|------------|
| Instalacja | Trzeba instalować Desktop/Docker | ✅ Gotowe online |
| Dostęp | Tylko z twojego PC | ✅ Z każdego miejsca (internet) |
| Backup | Ręczny | ✅ Automatyczny |
| Aktualizacje | Ręczne | ✅ Automatyczne |
| Limit (free) | Bez limitu | 200k nodes + 400k relationships |
| Wydajność | Lokalna szybkość | Zależna od internetu |

## Trwałe ustawienie hasła (opcjonalnie)

### Opcja A: .env plik (zalecane)

1. Stwórz plik `.env` w katalogu głównym:
   ```
   NEO4J_PASSWORD=twoje_haslo
   ```

2. Dodaj do `.gitignore`:
   ```
   .env
   ```

3. Zainstaluj python-dotenv:
   ```bash
   pip install python-dotenv
   ```

4. Załaduj w skrypcie (dodaj na początku):
   ```python
   from dotenv import load_dotenv
   load_dotenv()
   ```

### Opcja B: Zmienna systemowa Windows

1. Otwórz: **System Properties** → **Environment Variables**
2. Dodaj nową zmienną użytkownika:
   - Nazwa: `NEO4J_PASSWORD`
   - Wartość: `twoje_haslo`
3. Zrestartuj PowerShell

## Limity AuraDB Free

- ✅ 200,000 węzłów
- ✅ 400,000 relacji  
- ✅ Backupy automatyczne
- ✅ Certyfikat SSL
- ❌ Multi-database (tylko `neo4j`)
- ❌ Analityka zaawansowana

**Dla RUSSINT:** Wystarczy na kilka tysięcy osób/organizacji/wydarzeń! 

## Przykładowe zapytania

### Sprawdź co jest w bazie
```cypher
MATCH (n)
RETURN labels(n) as Type, count(*) as Count
```

### Organizacje i ich profile
```cypher
MATCH (o:Organization)-[:HAS_PROFILE]->(p:Profile)
RETURN o.name, p.name, p.url
```

### Wydarzenia z najwyższą liczbą prelegentów
```cypher
MATCH (e:Event)<-[:SPEAKER_AT]-(p:Person)
WITH e, count(p) as speakerCount
RETURN e.name, e.date_start, speakerCount
ORDER BY speakerCount DESC
```

## Backup i export

### Eksport do CSV (przez Cypher)
```cypher
// Nodes
MATCH (n:Entity)
RETURN n.id, n.name, n.entity_type
```
Kliknij **Download CSV**

### Eksport całej bazy (przez Console)
1. Console → Instance → **Export**
2. Wybierz format: JSON lub CSV
3. Download

## Troubleshooting

### "Authentication failed"
- Sprawdź hasło: `echo $env:NEO4J_PASSWORD`
- Zresetuj hasło w Console
- Upewnij się że brak spacji w haśle

### "Unable to connect"
- Sprawdź czy instancja działa (Status: **Running** w Console)
- Sprawdź połączenie: `Test-NetConnection 1f589f65.databases.neo4j.io -Port 7687`

### "Database limit exceeded"
- Free tier: 200k nodes, 400k relationships
- Wyczyść starą bazę: `MATCH (n) DETACH DELETE n`
- Lub upgrade do płatnego planu

## Przydatne linki

- Neo4j Aura Console: https://console-preview.neo4j.io/
- Dokumentacja Aura: https://neo4j.com/docs/aura/
- Cypher Cheat Sheet: https://neo4j.com/docs/cypher-cheat-sheet/

---

**Gotowe!** Teraz masz bazę grafową w chmurze dostępną z każdego miejsca. 🎉
