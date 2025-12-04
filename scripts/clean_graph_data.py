import json
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
NODES_FILE = RAW_DIR / "graph_nodes.json"
EDGES_FILE = RAW_DIR / "graph_edges.json"

def load_json(path):
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def clean_data():
    print("Cleaning graph data...")
    
    nodes = load_json(NODES_FILE)
    edges = load_json(EDGES_FILE)
    
    # 1. Deduplicate Nodes by ID
    unique_nodes = {}
    for n in nodes:
        if 'id' in n:
            unique_nodes[n['id']] = n
    
    print(f"Nodes: {len(nodes)} -> {len(unique_nodes)}")
    
    # 2. Deduplicate Edges by ID (or signature)
    unique_edges = {}
    for e in edges:
        eid = e.get('id')
        if not eid:
            eid = f"{e.get('source_id')}-{e.get('relationship_type')}-{e.get('target_id')}"
            e['id'] = eid
        unique_edges[eid] = e
        
    print(f"Edges: {len(edges)} -> {len(unique_edges)}")
    
    # 3. Validate Naming Convention (Basic check)
    # Ensure 'person' type has 'ent-' prefix (as per instructions)
    # Ensure 'organization' has 'org-'
    # Ensure 'post' has 'post-'
    # Ensure 'event' has 'evt-'
    # Ensure 'profile' has 'profile-'
    
    final_nodes = list(unique_nodes.values())
    
    for n in final_nodes:
        nid = n.get('id', '')
        ntype = n.get('entity_type', '')
        
        if ntype == 'person' and not nid.startswith('ent-'):
            print(f"[WARN] Person ID does not start with 'ent-': {nid}")
        elif ntype == 'organization' and not nid.startswith('org-'):
            print(f"[WARN] Organization ID does not start with 'org-': {nid}")
        elif ntype == 'post' and not nid.startswith('post-'):
            print(f"[WARN] Post ID does not start with 'post-': {nid}")
        elif ntype == 'event' and not nid.startswith('evt-'):
            print(f"[WARN] Event ID does not start with 'evt-': {nid}")
        elif ntype == 'profile' and not nid.startswith('profile-'):
            print(f"[WARN] Profile ID does not start with 'profile-': {nid}")

    # Save back
    save_json(NODES_FILE, final_nodes)
    save_json(EDGES_FILE, list(unique_edges.values()))
    print("Cleanup complete.")

if __name__ == "__main__":
    clean_data()
