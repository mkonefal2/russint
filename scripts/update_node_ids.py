"""
Script to update node `id` and `name` properties in Neo4j according to a provided mapping.
This will rename nodes in-place (useful to normalize IDs without recreating nodes).
"""
from neo4j import GraphDatabase
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://1f589f65.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "YOUR_PASSWORD_HERE")

if not NEO4J_PASSWORD or NEO4J_PASSWORD == "YOUR_PASSWORD_HERE":
    print("⚠️  Brak poprawnej wartości NEO4J_PASSWORD w .env lub zmiennych środowiskowych. Uzupełnij plik .env i spróbuj ponownie.")
    raise SystemExit(1)


MAPPINGS = [
    # (old_id, new_id, new_name)
    ("post-20240418", "post-002", "Post: ABW wtargnęła do naszych domów o 6 rano"),
    ("post-20240113", "post-003", "Post: To jest zamach na polskie rodziny"),
    ("fb_BraterstwaLudziWolnych_pfbid02S7DuXzZkjeeod95uhipsAvELgdLk5rL4Tgstt2qAv85WJhotUZgdjn7csi1HWziyl", "post-004", "Repost: twierdzenia o 'PsyOp' i 'pseudo-elity' (udostępnienie Jakuba Kuśpita)"),
    ("post-orig-001-jakub-kuspit", "post-005", "Post: Jakub Kuśpit — twierdzenia o 'PsyOp'")
]


def run_mapping(uri, user, password, mappings):
    driver = GraphDatabase.driver(uri, auth=(user, password))
    try:
        with driver.session() as session:
            for old_id, new_id, new_name in mappings:
                # Check if new_id already exists
                res = session.run("MATCH (n {id: $new_id}) RETURN count(n) AS cnt", new_id=new_id)
                if res.single()["cnt"] > 0:
                    print(f"⚠️ New id {new_id} already exists — skipping mapping for {old_id} -> {new_id}")
                    continue

                # Update node id and name
                print(f"Renaming {old_id} -> {new_id} and setting name to '{new_name}'")
                session.run(
                    "MATCH (n {id: $old_id}) SET n.id = $new_id, n.name = $new_name RETURN n",
                    old_id=old_id, new_id=new_id, new_name=new_name
                )
    finally:
        driver.close()


if __name__ == '__main__':
    run_mapping(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, MAPPINGS)
