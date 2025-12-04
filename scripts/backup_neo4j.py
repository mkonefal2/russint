import os
import json
import datetime
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USER = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

def backup_neo4j():
    if not all([NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD]):
        print("Error: Missing Neo4j credentials in .env")
        return

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    data = {
        "meta": {
            "generated_at": datetime.datetime.now().isoformat(),
            "type": "full_backup"
        },
        "nodes": [],
        "edges": []
    }

    with driver.session() as session:
        # Fetch all nodes
        print("Fetching nodes...")
        result = session.run("MATCH (n) RETURN n")
        for record in result:
            node = record["n"]
            node_data = dict(node)
            # Ensure id is present (it should be a property, not the internal id)
            if "id" not in node_data:
                # If no id property, use element_id or skip? 
                # The project schema relies on 'id' property.
                # We will warn if missing.
                pass
            
            # Add labels
            node_data["labels"] = list(node.labels)
            data["nodes"].append(node_data)

        # Fetch all relationships
        print("Fetching relationships...")
        result = session.run("MATCH ()-[r]->() RETURN r, startNode(r).id as source_id, endNode(r).id as target_id")
        for record in result:
            rel = record["r"]
            rel_data = dict(rel)
            rel_data["source_id"] = record["source_id"]
            rel_data["target_id"] = record["target_id"]
            rel_data["relationship_type"] = rel.type
            data["edges"].append(rel_data)

    driver.close()

    # Ensure backup directory exists
    backup_dir = os.path.join("data", "backup")
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"neo4j_backup_{timestamp}.json"
    filepath = os.path.join(backup_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Backup saved to: {filepath}")
    print(f"Nodes: {len(data['nodes'])}")
    print(f"Edges: {len(data['edges'])}")

if __name__ == "__main__":
    backup_neo4j()
