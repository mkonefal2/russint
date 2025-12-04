import json
from pathlib import Path
from datetime import datetime

# Paths
BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
INCREMENTS_DIR = BASE_DIR / "data" / "processed" / "graph_increments"
INCREMENTS_DIR.mkdir(parents=True, exist_ok=True)

NODES_FILE = RAW_DIR / "graph_nodes.json"
EDGES_FILE = RAW_DIR / "graph_edges.json"

def load_json(path):
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_increment(name, nodes, edges):
    data = {
        "meta": {
            "source": "split_script",
            "generated_at": datetime.now().isoformat(),
            "description": f"Split data for {name}"
        },
        "nodes": nodes,
        "edges": edges
    }
    # Sanitize filename
    safe_name = "".join([c if c.isalnum() or c in ('-', '_') else '_' for c in name])
    filename = f"analysis_{safe_name}.json"
    
    with open(INCREMENTS_DIR / filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print("Loading global graph data...")
    all_nodes = load_json(NODES_FILE)
    all_edges = load_json(EDGES_FILE)
    
    nodes_map = {n['id']: n for n in all_nodes}
    
    # Ensure all edges have IDs
    for e in all_edges:
        if 'id' not in e:
            e['id'] = f"{e['source_id']}-{e['relationship_type']}-{e['target_id']}"

    # Track which items have been assigned to a file
    assigned_node_ids = set()
    assigned_edge_ids = set()
    
    # 1. Process Posts
    posts = [n for n in all_nodes if n.get('entity_type') == 'post']
    print(f"Found {len(posts)} posts. Creating individual files...")
    
    for post in posts:
        post_id = post['id']
        
        # Find related edges (connected to the post)
        related_edges = []
        for e in all_edges:
            if e['source_id'] == post_id or e['target_id'] == post_id:
                related_edges.append(e)
        
        # Find related nodes (neighbors)
        related_node_ids = set()
        related_node_ids.add(post_id)
        
        for e in related_edges:
            related_node_ids.add(e['source_id'])
            related_node_ids.add(e['target_id'])
            assigned_edge_ids.add(e['id']) # Mark edge as assigned
            
        # Build lists
        current_nodes = []
        for nid in related_node_ids:
            if nid in nodes_map:
                current_nodes.append(nodes_map[nid])
                assigned_node_ids.add(nid) # Mark node as assigned
        
        # Save file
        save_increment(post_id, current_nodes, related_edges)

    # 2. Process Remaining (Base/Structure)
    # Edges that were not assigned to any post (e.g. Org -> Profile, Person -> Event where Event is not linked to Post yet)
    remaining_edges = [e for e in all_edges if e['id'] not in assigned_edge_ids]
    
    # Nodes that are part of remaining edges OR were never assigned (orphans)
    remaining_node_ids = set()
    for e in remaining_edges:
        remaining_node_ids.add(e['source_id'])
        remaining_node_ids.add(e['target_id'])
    
    # Add any nodes that were not touched at all (orphans)
    for nid in nodes_map:
        if nid not in assigned_node_ids:
            remaining_node_ids.add(nid)
            
    remaining_nodes = []
    for nid in remaining_node_ids:
        if nid in nodes_map:
            remaining_nodes.append(nodes_map[nid])

    if remaining_edges or remaining_nodes:
        print(f"Saving remaining base structure ({len(remaining_nodes)} nodes, {len(remaining_edges)} edges)...")
        save_increment("base_structure", remaining_nodes, remaining_edges)
    
    print("Split complete. Files generated in data/processed/graph_increments/")

if __name__ == "__main__":
    main()
