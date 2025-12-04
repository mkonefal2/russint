import json
import os
import glob
from pathlib import Path
from load_to_neo4j_incremental import IncrementalLoader, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

BASE_DIR = Path(__file__).parent.parent
INCREMENTS_DIR = BASE_DIR / "src" / "ui" / "static" / "data" / "processed" / "graph_increments"

def main():
    # Find latest incremental file
    files = list(INCREMENTS_DIR.glob("analysis_match_images_by_id_*.json"))
    if not files:
        print("No incremental files found in", INCREMENTS_DIR)
        return

    latest_file = max(files, key=os.path.getctime)
    print(f"Processing latest incremental file: {latest_file}")

    with open(latest_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    nodes = data.get('nodes', [])
    edges = data.get('edges', [])

    print(f"Found {len(nodes)} nodes and {len(edges)} edges.")

    # Create temp files
    temp_nodes_path = Path("temp_nodes.json")
    temp_edges_path = Path("temp_edges.json")

    with open(temp_nodes_path, 'w', encoding='utf-8') as f:
        json.dump(nodes, f, ensure_ascii=False)
    
    with open(temp_edges_path, 'w', encoding='utf-8') as f:
        json.dump(edges, f, ensure_ascii=False)

    # Load to Neo4j
    loader = IncrementalLoader(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        loader.create_constraints()
        if nodes:
            print("Loading nodes...")
            loader.load_entities(temp_nodes_path)
        if edges:
            print("Loading edges...")
            loader.load_relationships(temp_edges_path)
    finally:
        loader.close()
        # Cleanup
        if temp_nodes_path.exists():
            temp_nodes_path.unlink()
        if temp_edges_path.exists():
            temp_edges_path.unlink()

if __name__ == "__main__":
    main()
