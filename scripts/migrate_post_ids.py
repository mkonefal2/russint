from neo4j import GraphDatabase
import os
import re
from dotenv import load_dotenv

load_dotenv()

uri = os.getenv("NEO4J_URI")
user = os.getenv("NEO4J_USER")
password = os.getenv("NEO4J_PASSWORD")

driver = GraphDatabase.driver(uri, auth=(user, password))

def migrate_ids(tx):
    # 1. Find the current max short ID (ignoring the 7777777 outlier if possible, or just starting from a safe number like 100)
    # Let's start from 100 to be safe and distinct from manual single digits
    next_id_num = 100
    
    print("--- Starting Migration ---")
    
    # Get all posts
    result = tx.run("MATCH (n:Post) RETURN n.id, n.screenshot")
    
    posts_to_update = []
    
    for record in result:
        old_id = record['n.id']
        screenshot = record['n.screenshot']
        
        # Check if it needs migration
        # We want to migrate anything that is NOT post-XXX (where XXX is 3 digits)
        # We will also migrate post-7777777... and post-fb_...
        
        if re.match(r'^post-\d{3}$', old_id):
            continue # Already good format
            
        posts_to_update.append((old_id, screenshot))
        
    print(f"Found {len(posts_to_update)} posts to migrate.")
    
    for old_id, screenshot in posts_to_update:
        new_id = f"post-{next_id_num:03d}"
        next_id_num += 1
        
        print(f"Migrating {old_id} -> {new_id}")
        
        # If screenshot is missing, try to infer it from old_id if it was a facebook ID
        new_screenshot = screenshot
        if not new_screenshot:
            if old_id.startswith("fb_"):
                parts = old_id.split('_')
                if len(parts) >= 3:
                    handle = parts[1]
                    new_screenshot = f"data/evidence/facebook/{handle}/{old_id}.png"
            elif old_id.startswith("post-fb_"):
                 # Extract the fb_ part
                 real_fb_id = old_id.replace("post-", "")
                 parts = real_fb_id.split('_')
                 if len(parts) >= 3:
                    handle = parts[1]
                    new_screenshot = f"data/evidence/facebook/{handle}/{real_fb_id}.png"

        
        # Update query
        tx.run("""
            MATCH (n:Post {id: $old_id})
            SET n.id = $new_id,
                n.original_id = $old_id,
                n.screenshot = $screenshot
            RETURN n
        """, old_id=old_id, new_id=new_id, screenshot=new_screenshot)
        
        print(f"Updated {old_id} to {new_id} (Screenshot: {new_screenshot})")

with driver.session() as session:
    session.execute_write(migrate_ids)

driver.close()
