import time
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv("../.env") if os.path.exists("../.env") else load_dotenv()

uri = os.getenv('NEO4J_URI')
user = os.getenv('NEO4J_USER')
password = os.getenv('NEO4J_PASSWORD')

print('NEO4J_URI=', uri)
print('NEO4J_USER=', user)

if not uri or not user or not password:
    print('Missing credentials')
    raise SystemExit(1)

print('Creating driver...')
start = time.time()
try:
    driver = GraphDatabase.driver(uri, auth=(user, password))
    print('Driver created in', time.time()-start)
except Exception as e:
    print('Driver creation failed:', e)
    raise

def run_query(q):
    with driver.session() as session:
        t0 = time.time()
        try:
            r = session.run(q).single()
            dt = time.time()-t0
            print(f"Query succeeded in {dt:.3f}s -> {r}")
        except Exception as e:
            print('Query error:', e)

print('\nRunning test queries')
run_query('RETURN 1 AS one')
run_query('MATCH (n) RETURN count(n) AS c')
run_query('MATCH ()-[r]->() RETURN count(r) AS c')

print('\nDone')

try:
    driver.close()
except:
    pass
