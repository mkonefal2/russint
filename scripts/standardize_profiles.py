import json
from pathlib import Path
import re

INCREMENTS_DIR = Path(__file__).parent.parent / "data" / "processed" / "graph_increments"

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def standardize_name(name, platform):
    # Remove existing prefixes if any
    clean_name = name
    prefixes = ["FB:", "YT:", "YouTube Channel:", "YouTube:", "Facebook:", "X:", "TW:", "IG:"]
    
    for p in prefixes:
        if clean_name.startswith(p):
            clean_name = clean_name[len(p):].strip()
            break # Only remove one prefix
            
    # Add correct prefix
    if platform == 'facebook':
        return f"FB: {clean_name}"
    elif platform == 'youtube':
        return f"YT: {clean_name}"
    elif platform == 'twitter' or platform == 'x':
        return f"X: {clean_name}"
    elif platform == 'instagram':
        return f"IG: {clean_name}"
    elif platform == 'tiktok':
        return f"TT: {clean_name}"
    elif platform == 'telegram':
        return f"TG: {clean_name}"
        
    return name # No change if unknown platform

def main():
    print("Standardizing Social Media Profiles...")
    
    # We need to track name changes to update edges
    # id -> new_name
    name_changes = {} 
    
    # 1. First pass: Update Nodes
    for file_path in INCREMENTS_DIR.glob("*.json"):
        data = load_json(file_path)
        modified = False
        
        for n in data.get('nodes', []):
            ntype = n.get('entity_type')
            platform = n.get('platform', '').lower()
            
            # Convert Channel to Profile
            if ntype == 'channel':
                n['entity_type'] = 'profile'
                if not platform:
                    if 'youtube' in n.get('url', ''):
                        platform = 'youtube'
                        n['platform'] = 'youtube'
                ntype = 'profile' # Update local var
                modified = True
                
            # Convert Page to Profile ONLY if it is Facebook
            if ntype == 'page' and platform == 'facebook':
                n['entity_type'] = 'profile'
                ntype = 'profile'
                modified = True

            # Standardize Name for Profiles
            if ntype == 'profile':
                old_name = n.get('name', '')
                new_name = standardize_name(old_name, platform)
                
                if new_name != old_name:
                    n['name'] = new_name
                    name_changes[n['id']] = new_name
                    modified = True
        
        if modified:
            save_json(file_path, data)

    print(f"Updated node names for {len(name_changes)} entities.")

    # 2. Second pass: Update Edges (source_name, target_name)
    # We need to do this across all files because an edge might refer to a node defined elsewhere
    # But wait, edges in increments usually refer to nodes in the same increment OR base structure.
    # However, since we are iterating all files, we can just check all edges.
    
    for file_path in INCREMENTS_DIR.glob("*.json"):
        data = load_json(file_path)
        modified = False
        
        for e in data.get('edges', []):
            src_id = e.get('source_id')
            tgt_id = e.get('target_id')
            
            if src_id in name_changes:
                if e.get('source_name') != name_changes[src_id]:
                    e['source_name'] = name_changes[src_id]
                    modified = True
            
            if tgt_id in name_changes:
                if e.get('target_name') != name_changes[tgt_id]:
                    e['target_name'] = name_changes[tgt_id]
                    modified = True
                    
        if modified:
            print(f"Updating edges in {file_path.name}...")
            save_json(file_path, data)

    print("Standardization complete.")

if __name__ == "__main__":
    main()
