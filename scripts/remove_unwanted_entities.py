import json
from pathlib import Path

INCREMENTS_DIR = Path(__file__).parent.parent / "data" / "processed" / "graph_increments"

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print("Removing unwanted entities (screenshots)...")
    
    removed_nodes_count = 0
    removed_edges_count = 0

    for file_path in INCREMENTS_DIR.glob("*.json"):
        data = load_json(file_path)
        
        original_node_count = len(data.get('nodes', []))
        original_edge_count = len(data.get('edges', []))
        
        # Identify nodes to remove
        nodes_to_keep = []
        removed_ids = set()
        
        for n in data.get('nodes', []):
            # Filter condition: entity_type == 'screenshot'
            if n.get('entity_type') == 'screenshot':
                removed_ids.add(n['id'])
            else:
                nodes_to_keep.append(n)
        
        # Identify edges to remove (connected to removed nodes)
        edges_to_keep = []
        for e in data.get('edges', []):
            if e['source_id'] in removed_ids or e['target_id'] in removed_ids:
                pass # Drop this edge
            else:
                edges_to_keep.append(e)
        
        # Update data if changes occurred
        if len(nodes_to_keep) < original_node_count or len(edges_to_keep) < original_edge_count:
            data['nodes'] = nodes_to_keep
            data['edges'] = edges_to_keep
            
            removed_nodes_count += (original_node_count - len(nodes_to_keep))
            removed_edges_count += (original_edge_count - len(edges_to_keep))
            
            print(f"Updating {file_path.name} (Removed {original_node_count - len(nodes_to_keep)} nodes, {original_edge_count - len(edges_to_keep)} edges)")
            save_json(file_path, data)

    print(f"Cleanup complete. Removed {removed_nodes_count} nodes and {removed_edges_count} edges.")

if __name__ == "__main__":
    main()
