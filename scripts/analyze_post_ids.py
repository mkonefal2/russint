from neo4j import GraphDatabase
import os
import re
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(user, password))

def analyze_ids(tx):
    print("--- Existing Short IDs ---")
    result = tx.run("MATCH (n:Post) WHERE n.id STARTS WITH 'post-' RETURN n.id ORDER BY n.id")
    max_num = 0
    for record in result:
        id_str = record['n.id']
        # Look for post-XXX pattern
        match = re.match(r'post-(\d+)', id_str)
        if match:
            num = int(match.group(1))
            if num > max_num:
                max_num = num
            print(f"Found short ID: {id_str}")
        else:
            print(f"Other post- ID: {id_str}")
            
    print(f"\nMax Short ID Number: {max_num}")
    
    print("\n--- IDs to Migrate ---")
    # Find IDs that are NOT simple post-XXX (ignoring the ones we just found valid)
    result = tx.run("MATCH (n:Post) RETURN n.id")
    to_migrate = []
    for record in result:
        id_str = record['n.id']
        if not re.match(r'post-\d{3}$', id_str):
             to_migrate.append(id_str)
             
    print(f"Found {len(to_migrate)} IDs to migrate:")
    for mid in to_migrate[:10]:
        print(mid)
    if len(to_migrate) > 10:
        print("...")

with driver.session() as session:
    session.execute_read(analyze_ids)

driver.close()
