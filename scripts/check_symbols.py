from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv('NEO4J_URI'),
    auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
)

with driver.session() as session:
    result = session.run("""
        MATCH (n) 
        WHERE n.name CONTAINS 'Logo' OR n.name CONTAINS 'Grafika' OR n.name CONTAINS 'Symbol'
        RETURN n.id, n.name, n.entity_type
        LIMIT 20
    """)
    print("Symbol nodes in DB:")
    for r in result:
        print(f"  {r['n.id']} | {r['n.name']} | {r['n.entity_type']}")

driver.close()
