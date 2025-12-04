from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(user, password))

def check_ids(tx):
    result = tx.run("MATCH (n) WHERE n.name CONTAINS 'Jakub' RETURN n.id, n.name LIMIT 5")
    for record in result:
        print(f"ID: {record['n.id']}, Name: {record['n.name']}")

with driver.session() as session:
    session.execute_read(check_ids)

driver.close()
