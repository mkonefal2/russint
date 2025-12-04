import json
from pathlib import Path
import shutil

INCREMENTS_DIR = Path(__file__).parent.parent / "data" / "processed" / "graph_increments"

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    print("Scanning for duplicates...")
    
    all_nodes = {} # id -> node
    all_edges = [] # list of edges
    file_map = {} # id -> filename (where the node is defined)

    # 1. Load all data
    for file_path in INCREMENTS_DIR.glob("*.json"):
        data = load_json(file_path)
        for n in data.get('nodes', []):
            all_nodes[n['id']] = n
            file_map[n['id']] = file_path
        for e in data.get('edges', []):
            all_edges.append(e)

    # 2. Identify duplicates
    # Strategy: Group by (entity_type, url) for profiles/pages/posts
    #           Group by (entity_type, name) for others
    
    canonical_map = {} # old_id -> new_id
    
    groups = {}
    
    for nid, node in all_nodes.items():
        ntype = node.get('entity_type')
        key = None
        
        if ntype in ['profile', 'page', 'post', 'article'] and node.get('url'):
            key = (ntype, node.get('url').strip().rstrip('/'))
        elif ntype in ['organization', 'person', 'event']:
            key = (ntype, node.get('name').strip())
        
        if key:
            if key not in groups:
                groups[key] = []
            groups[key].append(nid)

    # 3. Create merge map
    for key, nids in groups.items():
        if len(nids) > 1:
            print(f"Found duplicate for {key}: {nids}")
            # Pick the one with the most descriptive ID or just the first one
            # Prefer IDs that are NOT generic like 'profile-001' if a better one exists
            
            best_id = nids[0]
            # Simple heuristic: prefer longer IDs (often contain slugs) or specific prefixes
            # But 'profile-001' is short. 'profile-braterstwa-ludzi-wolnych' is long.
            # Let's prefer the one that is NOT matching regex '.*-\d+$' if possible, or just length.
            
            sorted_ids = sorted(nids, key=len, reverse=True) 
            # e.g. ['profile-braterstwa-ludzi-wolnych', 'profile-001']
            best_id = sorted_ids[0]
            
            for nid in nids:
                if nid != best_id:
                    canonical_map[nid] = best_id

    print(f"Identified {len(canonical_map)} nodes to merge.")

    if not canonical_map:
        print("No duplicates found.")
        return

    # 4. Apply changes to files
    for file_path in INCREMENTS_DIR.glob("*.json"):
        data = load_json(file_path)
        modified = False
        
        new_nodes = []
        for n in data.get('nodes', []):
            nid = n['id']
            if nid in canonical_map:
                # This node is being merged into another.
                # We only keep it if it IS the canonical one (which shouldn't happen if we iterate correctly)
                # OR if we are in the file that owns the canonical one?
                # Actually, we should just update the ID. But if the canonical node is already in this file, we have a duplicate in the list.
                # If the canonical node is NOT in this file, we rename this node to canonical ID.
                # But wait, if we rename, we might have 2 definitions of the same node across files.
                # That's fine for Neo4j (MERGE), but for our file structure, we might want to consolidate.
                # For now, let's just rename.
                n['id'] = canonical_map[nid]
                modified = True
            new_nodes.append(n)
        
        # Deduplicate nodes within the file after renaming
        unique_nodes = {}
        for n in new_nodes:
            if n['id'] not in unique_nodes:
                unique_nodes[n['id']] = n
            else:
                # Merge properties if needed?
                pass
        data['nodes'] = list(unique_nodes.values())

        # Update edges
        new_edges = []
        for e in data.get('edges', []):
            src = e['source_id']
            tgt = e['target_id']
            
            if src in canonical_map:
                e['source_id'] = canonical_map[src]
                modified = True
            if tgt in canonical_map:
                e['target_id'] = canonical_map[tgt]
                modified = True
            
            # Update ID of edge to reflect new source/target
            # e['id'] = f"{e['source_id']}-{e['relationship_type']}-{e['target_id']}" 
            # (Optional, but good for consistency)
            
            new_edges.append(e)
            
        data['edges'] = new_edges
        
        if modified:
            print(f"Updating {file_path.name}...")
            save_json(file_path, data)

    print("Merge complete.")

if __name__ == "__main__":
    main()
