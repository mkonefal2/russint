"""
RUSSINT - Neo4j Incremental Loader
Dodaje/aktualizuje węzły i relacje z JSON bez czyszczenia bazy.
"""

from neo4j import GraphDatabase
import json
from pathlib import Path
import os

# Załaduj .env, jeśli dostępne
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
ENTITIES_FILE = RAW_DIR / "entities.json"
RELATIONSHIPS_FILE = RAW_DIR / "relationships.json"

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://1f589f65.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "YOUR_PASSWORD_HERE")

if NEO4J_PASSWORD == "YOUR_PASSWORD_HERE":
    print("⚠️  UWAGA: Nie ustawiono hasła NEO4J_PASSWORD. Ustaw zmienną środowiskową i spróbuj ponownie.")
    raise SystemExit(1)


class IncrementalLoader:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_constraints(self):
        with self.driver.session() as session:
            constraints = [
                "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE",
                "CREATE CONSTRAINT organization_id IF NOT EXISTS FOR (o:Organization) REQUIRE o.id IS UNIQUE",
                "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE",
                "CREATE CONSTRAINT profile_id IF NOT EXISTS FOR (pr:Profile) REQUIRE pr.id IS UNIQUE",
                "CREATE CONSTRAINT event_id IF NOT EXISTS FOR (ev:Event) REQUIRE ev.id IS UNIQUE",
                "CREATE CONSTRAINT post_id IF NOT EXISTS FOR (po:Post) REQUIRE po.id IS UNIQUE",
            ]
            for c in constraints:
                try:
                    session.run(c)
                except Exception:
                    pass
            print("✅ Ograniczenia (jeśli brakowały) utworzone")

    def load_entities(self, entities_file):
        if not entities_file.exists():
            print("⚠️ Brak pliku entities.json")
            return 0

        with open(entities_file, 'r', encoding='utf-8') as f:
            entities = json.load(f)

        count = 0
        with self.driver.session() as session:
            for e in entities:
                entity_type = e.get('entity_type', 'unknown')
                label_map = {
                    'organization': 'Organization',
                    'person': 'Person',
                    'profile': 'Profile',
                    'event': 'Event',
                    'post': 'Post',
                    'page': 'Page',
                    'group': 'Group',
                    'channel': 'Channel'
                }
                label = label_map.get(entity_type, 'Entity')

                props = dict(e)  # copy all fields
                # sanitize props: convert nested dicts to JSON strings (Neo4j properties must be primitives or arrays)
                for k, v in list(props.items()):
                    if isinstance(v, dict):
                        try:
                            props[k] = json.dumps(v, ensure_ascii=False)
                        except Exception:
                            props.pop(k, None)
                    elif isinstance(v, list):
                        # keep lists of primitives only; otherwise stringify
                        if not all(isinstance(i, (str, int, float, bool, type(None))) for i in v):
                            try:
                                props[k] = json.dumps(v, ensure_ascii=False)
                            except Exception:
                                props.pop(k, None)
                # ensure id and name exist
                if 'id' not in props or props.get('id') is None:
                    print(f"⚠️ Pomijam encję bez id: {props.get('name')}")
                    continue

                # MERGE by id and set properties (merge will update existing)
                query = f"""
                MERGE (n:{label} {{id: $id}})
                SET n += $props
                """
                session.run(query, id=props['id'], props=props)
                count += 1

        print(f"✅ Załadowano/aktualizowano {count} węzłów")
        return count

    def load_relationships(self, relationships_file):
        if not relationships_file.exists():
            print("⚠️ Brak pliku relationships.json")
            return 0

        with open(relationships_file, 'r', encoding='utf-8') as f:
            relationships = json.load(f)

        count = 0
        with self.driver.session() as session:
            for r in relationships:
                rel_type = r.get('relationship_type', 'RELATED_TO')
                props = dict(r)
                # sanitize relationship props similarly
                for k, v in list(props.items()):
                    if isinstance(v, dict):
                        try:
                            props[k] = json.dumps(v, ensure_ascii=False)
                        except Exception:
                            props.pop(k, None)
                    elif isinstance(v, list):
                        if not all(isinstance(i, (str, int, float, bool, type(None))) for i in v):
                            try:
                                props[k] = json.dumps(v, ensure_ascii=False)
                            except Exception:
                                props.pop(k, None)
                # require source and target ids
                src = r.get('source_id') or r.get('source')
                tgt = r.get('target_id') or r.get('target')
                if not src or not tgt:
                    print(f"⚠️ Pomijam relację bez source/target: {r.get('id')}")
                    continue

                query = f"""
                MATCH (source {{id: $source_id}})
                MATCH (target {{id: $target_id}})
                MERGE (source)-[rel:{rel_type}]->(target)
                SET rel += $props
                """
                session.run(query, source_id=src, target_id=tgt, props=props)
                count += 1

        print(f"✅ Załadowano/aktualizowano {count} relacji")
        return count


def main():
    print("🎯 RUSSINT - Neo4j Incremental Loader")
    loader = IncrementalLoader(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        loader.create_constraints()
        print("📥 Ładowanie encji...")
        loader.load_entities(ENTITIES_FILE)
        print("📥 Ładowanie relacji...")
        loader.load_relationships(RELATIONSHIPS_FILE)
        print("✅ Zakończono incremental load")
    finally:
        loader.close()


if __name__ == '__main__':
    main()
