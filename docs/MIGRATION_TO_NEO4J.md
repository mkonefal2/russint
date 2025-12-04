# RUSSINT - Migracja do Neo4j

## Dlaczego Neo4j?

### DuckDB (obecne):
- ✅ Szybkie zapytania SQL
- ✅ Pliki lokalne
- ❌ Relacje jako tabele (nie natywne)
- ❌ Brak wizualizacji
- ❌ Ograniczone traversale grafu

### Neo4j (nowe):
- ✅ Natywna baza grafowa
- ✅ Cypher (język zapytań dla grafów)
- ✅ Wbudowana wizualizacja (Neo4j Browser)
- ✅ Zaawansowane traversale (ścieżki, wzorce)
- ✅ Indeksy na relacjach
- ✅ Skalowalność

## Kroki migracji

### 1. Instalacja Neo4j

**Opcja A: Neo4j Desktop (zalecane dla Windows)**
```bash
# Pobierz: https://neo4j.com/download/
# Zainstaluj, utwórz bazę, ustaw hasło
```

**Opcja B: Docker**
```bash
docker run -d \
  --name russint-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  -v neo4j_data:/data \
  neo4j:latest
```

### 2. Instalacja sterownika Python

```bash
pip install neo4j
```

### 3. Migracja danych

```bash
# Edytuj hasło w scripts/load_to_neo4j.py
# Zmień: NEO4J_PASSWORD = "password" na swoje hasło

# Uruchom migrację
python scripts/load_to_neo4j.py
```

Output:
```
==================================================
📊 RUSSINT - Neo4j Loader
==================================================
📁 URI: bolt://localhost:7687

🗑️ Wyczyszczono bazę Neo4j
✅ Utworzono ograniczenia

📥 Ładowanie danych...
✅ Załadowano 10 węzłów
✅ Załadowano 10 relacji

==================================================
📊 STATYSTYKI NEO4J
==================================================
🔵 Węzły (nodes): 10
🔗 Relacje (relationships): 10
```

### 4. Dostęp do Neo4j Browser

Otwórz: **http://localhost:7474**

Login:
- Username: `neo4j`
- Password: `password` (lub twoje)

### 5. Aplikacja Streamlit z Neo4j

```bash
# Edytuj hasło w src/ui/neo4j_editor_app.py
# Zmień: NEO4J_PASSWORD = "password"

# Uruchom aplikację
streamlit run src/ui/neo4j_editor_app.py
```

## Porównanie interfejsów

| Funkcja | DuckDB (stare) | Neo4j (nowe) |
|---------|----------------|--------------|
| Dodawanie węzłów | JSON ręcznie | Streamlit UI + Cypher |
| Relacje | JSON ręcznie | Streamlit UI + Cypher |
| Wizualizacja | Pyvis (statyczna) | Neo4j Browser (interaktywna) |
| Zapytania | SQL | Cypher |
| Ścieżki grafu | Trudne | `MATCH path = (a)-[*1..3]-(b)` |
| Eksport | CSV | CSV + Cypher dump |

## Przykładowe zapytania Cypher

### Znajdź organizację i jej profile
```cypher
MATCH (o:Organization)-[:HAS_PROFILE]->(p:Profile)
RETURN o, p
```

### Kto był prelegentem na jakich wydarzeniach?
```cypher
MATCH (p:Person)-[:SPEAKER_AT]->(e:Event)
RETURN p.name as Prelegent, collect(e.name) as Wydarzenia
```

### Znajdź ścieżki między dwoma osobami (max 4 kroki)
```cypher
MATCH path = shortestPath(
  (p1:Person {name: "Jakub Kuśpit"})-[*..4]-(p2:Person {name: "Mieczysław Bielak"})
)
RETURN path
```

### Wspólne wydarzenia dwóch osób
```cypher
MATCH (p1:Person)-[:SPEAKER_AT]->(e:Event)<-[:SPEAKER_AT]-(p2:Person)
WHERE p1.name = "Jakub Kuśpit" AND p2 <> p1
RETURN p2.name as Osoba, collect(e.name) as WspolneWydarzenia
```

### Które profile publikują najwięcej postów?
```cypher
MATCH (pr:Profile)-[:PUBLISHED]->(po:Post)
RETURN pr.name, count(po) as PostCount
ORDER BY PostCount DESC
```

## Backup i restore

### Backup
```bash
# Z Neo4j Desktop: Management → Dump
# Lub przez terminal:
neo4j-admin dump --database=neo4j --to=russint_backup.dump
```

### Restore
```bash
neo4j-admin load --from=russint_backup.dump --database=neo4j --force
```

## Co dalej?

1. ✅ Migracja danych JSON → Neo4j
2. ✅ Aplikacja Streamlit z Neo4j
3. 🔄 Automatyczny import z FB scraper → Neo4j
4. 🔄 Analiza community detection (Louvain, PageRank)
5. 🔄 Timeline analysis (kiedy kto z kim)
6. 🔄 Export do Gephi (bezpośrednio z Neo4j)

## FAQ

**Q: Czy mogę używać obu (DuckDB + Neo4j)?**
A: Tak! DuckDB dla analiz SQL, Neo4j dla grafu.

**Q: Jak wrócić do JSON?**
A: `MATCH (n) RETURN n` → eksport do JSON przez Streamlit lub Cypher Shell.

**Q: Neo4j vs Gephi?**
A: Neo4j = baza + wizualizacja + zapytania. Gephi = tylko wizualizacja (offline).

**Q: Wydajność?**
A: Neo4j jest szybszy dla traversali grafu (ścieżki, sąsiedztwo). DuckDB lepszy dla SQL agregacji.
