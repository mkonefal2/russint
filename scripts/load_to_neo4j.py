"""
RUSSINT - Neo4j Loader
Ładuje dane z JSON (entities, relationships) do bazy grafowej Neo4j.
"""

from neo4j import GraphDatabase
import json
from pathlib import Path
from datetime import datetime
import os

# Załaduj zmienne z .env jeśli istnieje
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv nie jest wymagany, można używać zmiennych systemowych

# Ścieżki
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
INCREMENTS_DIR = PROCESSED_DIR / "graph_increments"
TRACKING_FILE = PROCESSED_DIR / "loaded_files.txt"

ENTITIES_FILE = RAW_DIR / "graph_nodes.json"
RELATIONSHIPS_FILE = RAW_DIR / "graph_edges.json"

# Konfiguracja Neo4j Aura - użyj zmiennych środowiskowych lub wartości domyślnych
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://1f589f65.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "YOUR_PASSWORD_HERE")

print(f"🔗 Łączę z: {NEO4J_URI}")
print(f"👤 Użytkownik: {NEO4J_USER}")

if NEO4J_PASSWORD == "YOUR_PASSWORD_HERE":
    print("⚠️  UWAGA: Nie ustawiono hasła!")
    print("   Możesz:")
    print("   1. Ustawić zmienną środowiskową: $env:NEO4J_PASSWORD='twoje_haslo'")
    print("   2. Lub edytować NEO4J_PASSWORD w tym pliku")
    exit(1)


class Neo4jLoader:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def clear_database(self):
        """Czyści całą bazę (OSTROŻNIE!)"""
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            print("🗑️ Wyczyszczono bazę Neo4j")
    
    def create_constraints(self):
        """Tworzy ograniczenia unikalności"""
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
                "CREATE CONSTRAINT organization_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
                "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT profile_id IF NOT EXISTS FOR (pr:Profile) REQUIRE pr.id IS UNIQUE",
                "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (ev:Event) REQUIRE ev.id IS UNIQUE",
                "CREATE CONSTRAINT post_id IF NOT EXISTS FOR (po:Post) REQUIRE po.id IS UNIQUE",
                "CREATE CONSTRAINT site_id IF NOT EXISTS FOR (s:Site) REQUIRE s.id IS UNIQUE",
                "CREATE CONSTRAINT video_id IF NOT EXISTS FOR (v:Video) REQUIRE v.id IS UNIQUE",
            ]
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception as e:
                    # Constraint może już istnieć
                    pass
            print("✅ Utworzono ograniczenia")
    
    def load_entities_from_list(self, entities):
        """Ładuje węzły (entities) z listy słowników"""
        count = 0
        with self.driver.session() as session:
            for e in entities:
                entity_type = e.get('entity_type', 'unknown')
                # Mapowanie typów na etykiety Neo4j
                label_map = {
                    'organization': 'Organization',
                    'person': 'Person',
                    'profile': 'Profile',
                    'event': 'Event',
                    'post': 'Post',
                    'page': 'Site',     # Map page to Site as requested
                    'group': 'Group',
                    'channel': 'Channel',
                    'site': 'Site',
                    'video': 'Video'
                }
                label = label_map.get(entity_type, 'Entity')
                
                # Przygotuj właściwości
                props = {
                    'id': e.get('id'),
                    'name': e.get('name'),
                    'entity_type': entity_type,
                    'description': e.get('description', ''),
                    'country': e.get('country', ''),
                    'first_seen': e.get('first_seen', ''),
                    'notes': e.get('notes', '')
                }
                
                # Dodatkowe pola zależne od typu
                if 'url' in e:
                    props['url'] = e['url']
                if 'platform' in e:
                    props['platform'] = e['platform']
                if 'category' in e:
                    props['category'] = e['category']
                if 'date_start' in e:
                    props['date_start'] = e['date_start']
                if 'date_end' in e:
                    props['date_end'] = e['date_end']
                if 'location' in e:
                    props['location'] = e['location']
                if 'date_posted' in e:
                    props['date_posted'] = e['date_posted']
                if 'handle' in e:
                    props['handle'] = e['handle']
                if 'parent_org_id' in e:
                    props['parent_org_id'] = e['parent_org_id']
                
                # Twórz węzeł tylko z jedną specyficzną etykietą
                query = f"""
                MERGE (n:{label} {{id: $id}})
                SET n += $props
                """
                session.run(query, id=props['id'], props=props)
                count += 1
        return count

    def load_entities(self, entities_file):
        """Ładuje węzły (entities) z JSON"""
        if not entities_file.exists():
            print("⚠️ Brak pliku entities.json")
            return 0
        
        with open(entities_file, 'r', encoding='utf-8') as f:
            entities = json.load(f)
        
        count = self.load_entities_from_list(entities)
        print(f"✅ Załadowano {count} węzłów z {entities_file.name}")
        return count
    
    def load_relationships_from_list(self, relationships):
        """Ładuje relacje z listy słowników"""
        count = 0
        with self.driver.session() as session:
            for r in relationships:
                rel_type = r.get('relationship_type', 'RELATED_TO')
                
                props = {
                    'date': r.get('date', ''),
                    'confidence': r.get('confidence', 1.0),
                    'evidence': r.get('evidence', ''),
                    'source_name': r.get('source_name', ''),
                    'target_name': r.get('target_name', '')
                }
                
                if 'event_id' in r:
                    props['event_id'] = r['event_id']
                if 'event_name' in r:
                    props['event_name'] = r['event_name']
                
                # Twórz relację - szukaj węzłów po ID bez względu na etykietę
                query = f"""
                MATCH (source {{id: $source_id}})
                MATCH (target {{id: $target_id}})
                MERGE (source)-[r:{rel_type}]->(target)
                SET r += $props
                """
                
                session.run(
                    query,
                    source_id=r.get('source_id'),
                    target_id=r.get('target_id'),
                    props=props
                )
                count += 1
        return count

    def load_relationships(self, relationships_file):
        """Ładuje relacje z JSON"""
        if not relationships_file.exists():
            print("⚠️ Brak pliku relationships.json")
            return 0
        
        with open(relationships_file, 'r', encoding='utf-8') as f:
            relationships = json.load(f)
        
        count = self.load_relationships_from_list(relationships)
        print(f"✅ Załadowano {count} relacji z {relationships_file.name}")
        return count

    def load_incremental(self):
        """Ładuje nowe pliki analizy z folderu INCREMENTS_DIR"""
        if not INCREMENTS_DIR.exists():
            print(f"⚠️ Folder {INCREMENTS_DIR} nie istnieje. Pomijam incremental load.")
            return

        # Wczytaj listę już załadowanych plików
        loaded_files = set()
        if TRACKING_FILE.exists():
            with open(TRACKING_FILE, 'r', encoding='utf-8') as f:
                loaded_files = set(line.strip() for line in f)

        # Znajdź nowe pliki
        new_files = []
        for json_file in INCREMENTS_DIR.glob('**/*.json'):
            # Używamy ścieżki względnej jako identyfikatora
            rel_path = str(json_file.relative_to(INCREMENTS_DIR))
            if rel_path not in loaded_files:
                new_files.append(json_file)
        
        if not new_files:
            print("ℹ️ Brak nowych plików do załadowania.")
            return

        print(f"📥 Znaleziono {len(new_files)} nowych plików do załadowania.")
        
        total_nodes = 0
        total_edges = 0
        file_data_cache = {}

        # Faza 1: Ładowanie węzłów ze wszystkich plików
        print("🔄 Faza 1: Ładowanie węzłów...")
        for json_file in new_files:
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    file_data_cache[json_file] = data
                
                nodes = data.get('nodes', [])
                # Jeśli format jest inny (np. lista węzłów), spróbuj zgadnąć
                if isinstance(data, list):
                    if data and 'entity_type' in data[0]:
                        nodes = data
                
                n_count = self.load_entities_from_list(nodes)
                total_nodes += n_count
                
            except Exception as e:
                print(f"❌ Błąd przy ładowaniu węzłów z {json_file.name}: {e}")

        # Faza 2: Ładowanie relacji ze wszystkich plików
        print("🔄 Faza 2: Ładowanie relacji...")
        for json_file in new_files:
            try:
                data = file_data_cache.get(json_file)
                if not data: continue

                edges = data.get('edges', [])
                # Jeśli format jest inny (np. lista węzłów), spróbuj zgadnąć
                if isinstance(data, list):
                    if data and 'source_id' in data[0]:
                        edges = data
                
                e_count = self.load_relationships_from_list(edges)
                total_edges += e_count
                
                # Zapisz jako załadowany
                with open(TRACKING_FILE, 'a', encoding='utf-8') as f:
                    f.write(str(json_file.relative_to(INCREMENTS_DIR)) + '\n')
                    
                n_count_display = len(data.get('nodes', [])) if isinstance(data, dict) else (len(data) if isinstance(data, list) and data and 'entity_type' in data[0] else 0)
                print(f"  - Załadowano {json_file.name}: {n_count_display} węzłów, {e_count} relacji")
                
            except Exception as e:
                print(f"❌ Błąd przy ładowaniu relacji z {json_file.name}: {e}")

        print(f"✅ Incremental load zakończony. Dodano łącznie: {total_nodes} węzłów, {total_edges} relacji.")
    
    def show_stats(self):
        """Wyświetla statystyki bazy"""
        with self.driver.session() as session:
            print("\n" + "="*50)
            print("📊 STATYSTYKI NEO4J")
            print("="*50)
            
            # Liczba węzłów
            result = session.run("MATCH (n) RETURN count(n) as count")
            print(f"🔵 Węzły (nodes): {result.single()['count']}")
            
            # Węzły wg typu
            result = session.run("""
                MATCH (n)
                RETURN COALESCE(n.entity_type, labels(n)[0]) as type, count(*) as count
                ORDER BY count DESC
            """)
            print("\n📊 Węzły wg typu:")
            for record in result:
                print(f"   - {record['type']}: {record['count']}")
            
            # Liczba relacji
            result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            print(f"\n🔗 Relacje (relationships): {result.single()['count']}")
            
            # Relacje wg typu
            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as rel_type, count(*) as count
                ORDER BY count DESC
            """)
            print("\n📊 Relacje wg typu:")
            for record in result:
                print(f"   - {record['rel_type']}: {record['count']}")
            
            # Top węzły (najwyższy stopień)
            result = session.run("""
                MATCH (n)
                OPTIONAL MATCH (n)-[r]->()
                WITH n, count(r) as out_degree
                RETURN n.name as name, out_degree
                ORDER BY out_degree DESC
                LIMIT 5
            """)
            print("\n🎯 Top węzły (najwyższy stopień wychodzący):")
            for record in result:
                print(f"   - {record['name']}: {record['out_degree']}")


def main():
    print("="*50)
    print("📊 RUSSINT - Neo4j Loader")
    print("="*50)
    print(f"📁 URI: {NEO4J_URI}")
    print()
    
    loader = Neo4jLoader(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        # Czyść bazę (opcjonalnie - zakomentuj jeśli nie chcesz)
        loader.clear_database()  # <--- ZAKOMENTOWANE: Nie czyść bazy przy każdym uruchomieniu
        
        # Utwórz ograniczenia
        loader.create_constraints()
        
        # Ładuj dane (Seed) - ZAKOMENTOWANE PO MIGRACJI
        print("\n📥 Ładowanie danych startowych (Seed)...")
        loader.load_entities(ENTITIES_FILE)
        loader.load_relationships(RELATIONSHIPS_FILE)
        
        # Ładuj dane przyrostowe
        print("\n📥 Ładowanie danych przyrostowych (Incremental)...")
        loader.load_incremental()
        
        # Pokaż statystyki
        loader.show_stats()
        
        print("\n✅ Zakończono!")
        print("\n💡 Otwórz Neo4j Browser: http://localhost:7474")
        print("   Przykładowe zapytania:")
        print("   MATCH (n) RETURN n LIMIT 25")
        print("   MATCH p=(n)-[r]->(m) RETURN p LIMIT 50")
        
    finally:
        loader.close()


if __name__ == "__main__":
    main()
