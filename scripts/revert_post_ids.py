from neo4j import GraphDatabase
import os
import re
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(user, password))

# Mappings for posts that don't have original_id stored in DB yet
# (old_short_id, new_long_id)
MANUAL_MAPPINGS = {
    "post-001": "fb_BraterstwaLudziWolnych_pfbid0219rwE34d48hfcTuUrccvvxgFizYcByeXwMTjzbrD9dX1ycUz9PvANH2Kw4KAJSN5l",
    "post-002": "fb_BraterstwaLudziWolnych_pfbid034KmeQ78vzhL5JGdzeQk7ovY52giHAuHjYiyvu9NcT3G2KFPiKsNXnukDm9Yvke2Zl",
    "post-003": "fb_BraterstwaLudziWolnych_pfbid071cebkweeCzVBJkff82MKmzwvPTpVi9NkdDTiQ76LEhZVxrXuASSki9ViV7t7Xx7l",
    "post-004": "fb_BraterstwaLudziWolnych_pfbid02S7DuXzZkjeeod95uhipsAvELgdLk5rL4Tgstt2qAv85WJhotUZgdjn7csi1HWziyl",
    "post-006": "fb_BraterstwaLudziWolnych_pfbid029XSpGTnfbFiUH4SiVRZ1Ahhu9FszHT958rdDE2dwk3xgp3YVfgpe6ev4MYMTQQ5l",
    # post-005 is special, it doesn't have a known FB ID in our previous scripts, skipping it for now or leaving as is.
}

def revert_ids(tx):
    print("--- Reverting IDs to Long Format ---")
    
    # Get all posts with short IDs
    result = tx.run("MATCH (n:Post) WHERE n.id STARTS WITH 'post-' RETURN n.id, n.original_id, n.screenshot")
    
    for record in result:
        current_id = record['n.id']
        original_id = record['n.original_id']
        screenshot = record['n.screenshot']
        
        new_id = None
        
        # 1. Try to use original_id if it looks like a FB ID
        if original_id and (original_id.startswith("fb_") or original_id.startswith("post-fb_")):
             new_id = original_id
             # Clean up post-fb_ prefix if present (from my previous migration script logic)
             if new_id.startswith("post-fb_"):
                 new_id = new_id.replace("post-fb_", "fb_")
        
        # 2. If no valid original_id, check manual mappings
        if not new_id and current_id in MANUAL_MAPPINGS:
            new_id = MANUAL_MAPPINGS[current_id]
            
        if new_id:
            print(f"Reverting {current_id} -> {new_id}")
            
            # Ensure screenshot path is correct
            # If we have a screenshot already, keep it.
            # If not, try to infer from the new long ID.
            final_screenshot = screenshot
            if not final_screenshot:
                 parts = new_id.split('_')
                 if len(parts) >= 3:
                    handle = parts[1]
                    final_screenshot = f"data/evidence/facebook/{handle}/{new_id}.png"
            
            tx.run("""
                MATCH (n:Post {id: $current_id})
                SET n.id = $new_id,
                    n.screenshot = $screenshot
                REMOVE n.original_id
                RETURN n
            """, current_id=current_id, new_id=new_id, screenshot=final_screenshot)
            print(f"Updated {current_id} to {new_id}")
        else:
            print(f"Skipping {current_id} (No mapping found)")

with driver.session() as session:
    session.execute_write(revert_ids)

driver.close()
