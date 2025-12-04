# 🕸️ RUSSINT - Neo4j Quick Start

## Czym jest Neo4j?

Neo4j to **baza grafowa** idealna do śledzenia relacji między ludźmi, organizacjami i wydarzeniami. W przeciwieństwie do zwykłych baz SQL, Neo4j:

- 🎯 Przechowuje **węzły** (osoby, organizacje, wydarzenia) i **relacje** (kto organizuje, kto mówi na)
- 🔍 Umożliwia **szybkie wyszukiwanie** połączeń (np. "kto jest związany z kim przez max 3 kroki")
- 👁️ Ma **wbudowaną wizualizację** - widzisz graf w przeglądarce
- 📊 Używa języka **Cypher** (jak SQL, ale dla grafów)

## Instalacja Neo4j (5 minut)

### Windows - Neo4j Desktop (najłatwiej)

1. Pobierz: https://neo4j.com/download/
2. Zainstaluj
3. Otwórz Neo4j Desktop
4. Kliknij: **New** → **Create Project**
5. Kliknij: **Add** → **Local DBMS**
6. Ustaw nazwę: `RUSSINT`
7. Ustaw hasło: `password` (zapamiętaj!)
8. Kliknij: **Create**
9. Kliknij: **Start** (zielony przycisk)

### Alternatywa - Docker

Jeśli masz Dockera:
```bash
docker run -d \
  --name russint-neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

## Ładowanie danych (30 sekund)

1. **Edytuj hasło** w pliku `scripts/load_to_neo4j.py`:
   ```python
   NEO4J_PASSWORD = "password"  # Zmień na swoje!
   ```

2. **Uruchom migrację**:
   ```bash
   python scripts/load_to_neo4j.py
   ```

3. Zobaczysz:
   ```
   ✅ Załadowano 10 węzłów
   ✅ Załadowano 10 relacji
   ```

## Dostęp do Neo4j Browser

1. Otwórz: **http://localhost:7474**
2. Login:
   - Username: `neo4j`
   - Password: `password` (lub twoje)

3. Wypróbuj zapytanie:
   ```cypher
   MATCH (n)-[r]->(m) 
   RETURN n, r, m 
   LIMIT 25
   ```

4. Kliknij **Execute** (▶)
5. Zobaczysz graf!

## Aplikacja Streamlit (UI do zarządzania)

1. **Edytuj hasło** w `src/ui/neo4j_editor_app.py`:
   ```python
   NEO4J_PASSWORD = "password"
   ```

2. **Uruchom aplikację**:
   ```bash
   streamlit run src/ui/neo4j_editor_app.py
   ```

3. Otwórz: **http://localhost:8501**

4. Możesz:
   - ➕ Dodawać nowe węzły (osoby, organizacje, wydarzenia)
   - 🔗 Tworzyć relacje między nimi
   - 🌐 Pisać własne zapytania Cypher
   - 📊 Oglądać statystyki

## Przykładowe zapytania Cypher

Wklej do Neo4j Browser (http://localhost:7474):

### Pokaż wszystko
```cypher
MATCH (n)-[r]->(m) 
RETURN n, r, m 
LIMIT 50
```

### Wydarzenia i prelegenci
```cypher
MATCH (e:Event)<-[:SPEAKER_AT]-(p:Person)
RETURN e.name as Wydarzenie, collect(p.name) as Prelegenci
```

### Organizacja → profil → post → wydarzenie
```cypher
MATCH path = (o:Organization)-[:HAS_PROFILE]->(pr:Profile)
             -[:PUBLISHED]->(po:Post)
             -[:ANNOUNCES]->(e:Event)
RETURN path
```

### Znajdź najaktywniejsze osoby
```cypher
MATCH (p:Person)-[r]->()
WITH p, count(r) as activity
RETURN p.name as Osoba, activity
ORDER BY activity DESC
LIMIT 10
```

### Kto z kim występował na wydarzeniach?
```cypher
MATCH (p1:Person)-[:SPEAKER_AT]->(e:Event)<-[:SPEAKER_AT]-(p2:Person)
WHERE p1 <> p2
RETURN p1.name, p2.name, collect(e.name) as WspolneWydarzenia
```

## Porównanie: JSON/DuckDB vs Neo4j

| Co chcesz zrobić | JSON/DuckDB | Neo4j |
|------------------|-------------|-------|
| Dodać osobę | Edytuj `entities.json` | Kliknij "Dodaj węzeł" w Streamlit |
| Dodać relację | Edytuj `relationships.json` | Kliknij "Dodaj relację" |
| Zobacz graf | `python visualize_network.py` | Otwórz Neo4j Browser |
| Znajdź ścieżki | Trudne (trzeba pisać kod) | `MATCH path = (a)-[*1..3]-(b)` |
| Eksport do Gephi | `data/export/nodes.csv` | To samo + Cypher export |

## Co dalej?

### Podstawowe
- ✅ Dodaj więcej osób przez Streamlit
- ✅ Dodaj więcej wydarzeń
- ✅ Dodaj relacje (kto z kim współpracuje)

### Zaawansowane
- 📊 Analiza community detection (grupy powiązanych osób)
- 🎯 PageRank (kto jest najważniejszy w sieci)
- 📈 Timeline analysis (jak sieć się rozwija w czasie)
- 🤖 Automatyczny import z Facebook scraper → Neo4j

## Pomoc

### Neo4j nie startuje?
- Sprawdź czy port 7687 jest wolny: `Test-NetConnection localhost -Port 7687`
- Sprawdź logi w Neo4j Desktop: Management → Logs

### Błąd połączenia w Pythonie?
- Upewnij się że Neo4j działa (Neo4j Browser odpowiada)
- Sprawdź hasło w `load_to_neo4j.py` i `neo4j_editor_app.py`

### Chcę wyczyścić bazę?
```cypher
MATCH (n) DETACH DELETE n
```
Potem ponownie: `python scripts/load_to_neo4j.py`

## Dokumentacja

- Neo4j Cypher Manual: https://neo4j.com/docs/cypher-manual/current/
- Neo4j Python Driver: https://neo4j.com/docs/python-manual/current/
- Przykłady Cypher: https://neo4j.com/graphgists/

---

**Potrzebujesz pomocy?** Zobacz `docs/MIGRATION_TO_NEO4J.md` dla szczegółów.
