from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(user, password))

def check_missing_screenshots(tx):
    print("--- Posts with missing screenshots ---")
    result = tx.run("""
        MATCH (n:Post) 
        WHERE n.screenshot IS NULL 
        AND NOT n.id STARTS WITH 'fb_'
        RETURN n.id, n.name
    """)
    for record in result:
        print(f"ID: {record['n.id']}, Name: {record['n.name']}")

with driver.session() as session:
    session.execute_read(check_missing_screenshots)

driver.close()
