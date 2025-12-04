import json
import os
from pathlib import Path
from datetime import datetime

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INCREMENTS_DIR = DATA_DIR / "processed" / "graph_increments"

NODES_FILE = RAW_DIR / "graph_nodes.json"
EDGES_FILE = RAW_DIR / "graph_edges.json"

def load_json(path):
    if not path.exists():
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_increment(filename, nodes, edges, source_desc):
    filepath = INCREMENTS_DIR / filename
    data = {
        "meta": {
            "source": "seed_migration",
            "description": source_desc,
            "generated_at": datetime.now().isoformat()
        },
        "nodes": nodes,
        "edges": edges
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"✅ Created {filename} ({len(nodes)} nodes, {len(edges)} edges)")

def main():
    print("🚀 Starting Seed Data Migration...")
    
    # Ensure output dir exists
    INCREMENTS_DIR.mkdir(parents=True, exist_ok=True)
    
    all_nodes = load_json(NODES_FILE)
    all_edges = load_json(EDGES_FILE)
    
    nodes_by_id = {n['id']: n for n in all_nodes}
    
    # Helper to find edges for a set of node IDs
    def get_edges_for_nodes(node_ids):
        relevant_edges = []
        for e in all_edges:
            if e.get('source_id') in node_ids and e.get('target_id') in node_ids:
                relevant_edges.append(e)
        return relevant_edges

    # Helper to find edges connected to a specific node ID (incoming or outgoing)
    def get_edges_connected_to(node_id):
        return [e for e in all_edges if e.get('source_id') == node_id or e.get('target_id') == node_id]

    processed_node_ids = set()

    # --- GROUP 1: ORGANIZATION & INFRASTRUCTURE ---
    # Org, Profiles, Pages (websites) linked to Org
    org_nodes = [n for n in all_nodes if n.get('entity_type') == 'organization']
    
    for org in org_nodes:
        cluster_ids = {org['id']}
        
        # Find children (profiles, pages with parent_org_id)
        for n in all_nodes:
            if n.get('parent_org_id') == org['id']:
                cluster_ids.add(n['id'])
        
        # Find edges connecting these
        cluster_edges = get_edges_for_nodes(cluster_ids)
        
        # Also include edges that define the structure (HAS_PROFILE etc) even if target isn't explicitly parented
        # (Though in our data they usually are).
        
        cluster_nodes = [nodes_by_id[nid] for nid in cluster_ids if nid in nodes_by_id]
        
        save_increment(
            f"analysis_{org['id']}.json",
            cluster_nodes,
            cluster_edges,
            f"Organization: {org.get('name')}"
        )
        processed_node_ids.update(cluster_ids)

    # --- GROUP 2: EVENTS ---
    event_nodes = [n for n in all_nodes if n.get('entity_type') == 'event']
    
    for evt in event_nodes:
        cluster_ids = {evt['id']}
        cluster_edges = []
        
        # Find speakers and organizers (edges connected to event)
        connected_edges = get_edges_connected_to(evt['id'])
        cluster_edges.extend(connected_edges)
        
        # Add the connected nodes (Speakers, etc.)
        for e in connected_edges:
            cluster_ids.add(e['source_id'])
            cluster_ids.add(e['target_id'])
            
        cluster_nodes = [nodes_by_id[nid] for nid in cluster_ids if nid in nodes_by_id]
        
        save_increment(
            f"analysis_{evt['id']}.json",
            cluster_nodes,
            cluster_edges,
            f"Event: {evt.get('name')}"
        )
        # We don't mark speakers as "processed" because they might appear in other contexts (posts)
        # But we mark the Event itself
        processed_node_ids.add(evt['id'])

    # --- GROUP 3: POSTS ---
    post_nodes = [n for n in all_nodes if n.get('entity_type') == 'post']
    
    for post in post_nodes:
        cluster_ids = {post['id']}
        cluster_edges = []
        
        # Find everything connected to the post
        connected_edges = get_edges_connected_to(post['id'])
        cluster_edges.extend(connected_edges)
        
        for e in connected_edges:
            cluster_ids.add(e['source_id'])
            cluster_ids.add(e['target_id'])
            
        cluster_nodes = [nodes_by_id[nid] for nid in cluster_ids if nid in nodes_by_id]
        
        # Sanitize filename (remove invalid chars if any)
        safe_id = post['id'].replace(':', '_').replace('/', '_')[-50:] # truncate if too long
        
        save_increment(
            f"analysis_{safe_id}.json",
            cluster_nodes,
            cluster_edges,
            f"Post: {post.get('name')}"
        )
        processed_node_ids.add(post['id'])

    # --- GROUP 4: LEFTOVERS (People, Pages not caught above) ---
    leftover_ids = set(nodes_by_id.keys()) - processed_node_ids
    # Note: Some people might have been included in Events/Posts but not marked as "processed" 
    # because we allowed duplication. Here we want nodes that were NEVER the "center" of a file.
    # Actually, let's just dump all People/Pages that are not Org/Event/Post into a misc file
    # to ensure their full properties are defined somewhere independent of events.
    
    misc_nodes = [n for n in all_nodes if n['id'] not in processed_node_ids and n.get('entity_type') not in ['organization', 'event', 'post']]
    
    if misc_nodes:
        # Find edges between misc nodes
        misc_ids = {n['id'] for n in misc_nodes}
        misc_edges = get_edges_for_nodes(misc_ids)
        
        save_increment(
            "analysis_seed_misc_entities.json",
            misc_nodes,
            misc_edges,
            "Miscellaneous Entities (People, Pages)"
        )

    print("🏁 Migration complete.")

if __name__ == "__main__":
    main()
