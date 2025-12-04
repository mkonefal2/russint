from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://1f589f65.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def list_potential_duplicates():
    with driver.session() as session:
        # 1. Check for nodes with only 'Entity' label (and no specific label)
        print("--- Nodes with only generic 'Entity' label ---")
        result = session.run("""
            MATCH (n:Entity)
            WHERE size(labels(n)) = 1
            RETURN n.id, n.name, labels(n)
        """)
        for record in result:
            print(f"ID: {record['n.id']}, Name: {record['n.name']}, Labels: {record['labels(n)']}")

        # 2. List all nodes by label to visually check for duplicates
        print("\n--- All Nodes by Label ---")
        result = session.run("""
            MATCH (n)
            RETURN labels(n) as labels, n.name as name, n.id as id
            ORDER BY labels(n), n.name
        """)
        
        nodes_by_label = {}
        for record in result:
            lbl = str(sorted(record['labels']))
            if lbl not in nodes_by_label:
                nodes_by_label[lbl] = []
            nodes_by_label[lbl].append(f"{record['name']} ({record['id']})")
            
        for lbl, nodes in nodes_by_label.items():
            print(f"\nLabel: {lbl}")
            for node in nodes:
                print(f"  - {node}")

    driver.close()

if __name__ == "__main__":
    list_potential_duplicates()
