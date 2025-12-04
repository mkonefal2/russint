from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(user, password))

def check_post(tx):
    name = "Repost: twierdzenia o 'PsyOp' i 'pseudo-elity' (udostępnienie Jakuba Kuśpita)"
    result = tx.run("MATCH (n:Post) WHERE n.name CONTAINS 'PsyOp' RETURN n.id, n.name, n.screenshot")
    for record in result:
        print(f"ID: {record['n.id']}")
        print(f"Name: {record['n.name']}")
        print(f"Screenshot Prop: {record['n.screenshot']}")

with driver.session() as session:
    session.execute_read(check_post)

driver.close()
