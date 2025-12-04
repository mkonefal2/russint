from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(user, password))

def update_url(tx):
    post_name = "Post: To jest zamach na polskie rodziny"
    new_url = "https://www.facebook.com/BraterstwaLudziWolnych/posts/pfbid06qTeJcfupgYUe4wnrk6EcP6xPACgHkxTiDA7A6xKrF1wjzeVhVGskS55nKeLHuhBl?locale=pl_PL"
    
    print(f"Searching for post: '{post_name}'")
    result = tx.run("MATCH (n:Post) WHERE n.name = $name RETURN n.id, n.url", name=post_name)
    
    found = False
    for record in result:
        found = True
        print(f"Found Post ID: {record['n.id']}")
        print(f"Current URL: {record['n.url']}")
        
        tx.run("MATCH (n:Post) WHERE n.name = $name SET n.url = $new_url", name=post_name, new_url=new_url)
        print(f"Updated URL to: {new_url}")
        
    if not found:
        print("Post not found!")

with driver.session() as session:
    session.execute_write(update_url)

driver.close()
