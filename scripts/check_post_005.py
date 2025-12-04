from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(user, password))

def check_post_005(tx):
    result = tx.run("MATCH (n:Post {id: 'post-005'}) RETURN n")
    for record in result:
        print(record['n'])

with driver.session() as session:
    session.execute_read(check_post_005)

driver.close()
