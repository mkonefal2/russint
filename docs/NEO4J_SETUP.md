# RUSSINT - Neo4j Setup

## Instalacja Neo4j

### Windows:
1. Pobierz Neo4j Desktop: https://neo4j.com/download/
2. Utwórz nową bazę danych (Project → Add → Local DBMS)
3. Ustaw hasło (np. "password")
4. Uruchom bazę (Start)

### Docker (alternatywa):
```bash
docker run -d \
  --name neo4j \
  -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

## Instalacja sterownika Python

```bash
pip install neo4j
```

## Konfiguracja

Edytuj `scripts/load_to_neo4j.py` i zmień hasło:
```python
NEO4J_PASSWORD = "twoje_haslo"
```

## Ładowanie danych

```bash
python scripts/load_to_neo4j.py
```

## Dostęp do Neo4j Browser

Otwórz: http://localhost:7474
- Username: `neo4j`
- Password: `password` (lub twoje)

## Przykładowe zapytania Cypher

### Wszystkie węzły i relacje
```cypher
MATCH (n)-[r]->(m) 
RETURN n, r, m 
LIMIT 100
```

### Organizacje i ich profile
```cypher
MATCH (o:Organization)-[:HAS_PROFILE]->(p:Profile)
RETURN o, p
```

### Wydarzenia i prelegenci
```cypher
MATCH (e:Event)<-[:SPEAKER_AT]-(p:Person)
RETURN e.name as Event, collect(p.name) as Speakers
```

### Ścieżki między węzłami
```cypher
MATCH path = (a:Organization)-[*1..3]-(b:Person)
WHERE a.name CONTAINS 'Braterstwa'
RETURN path
LIMIT 10
```

### Najaktywniejsze węzły
```cypher
MATCH (n)
OPTIONAL MATCH (n)-[r]->()
WITH n, count(r) as degree
RETURN n.name, n.entity_type, degree
ORDER BY degree DESC
LIMIT 10
```

### Wspólne wydarzenia
```cypher
MATCH (p1:Person)-[:SPEAKER_AT]->(e:Event)<-[:SPEAKER_AT]-(p2:Person)
WHERE p1 <> p2
RETURN p1.name, p2.name, collect(e.name) as CommonEvents
```

## Eksport danych

### CSV dla Gephi
```cypher
// Nodes
MATCH (n:Entity)
RETURN n.id as Id, n.name as Label, n.entity_type as Type

// Edges
MATCH (a)-[r]->(b)
RETURN a.id as Source, b.id as Target, type(r) as Type, r.confidence as Weight
```

## Backup

```bash
# Eksport całej bazy
neo4j-admin dump --database=neo4j --to=backup.dump

# Import
neo4j-admin load --from=backup.dump --database=neo4j --force
```
