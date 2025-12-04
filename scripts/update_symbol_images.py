"""
Update symbol nodes with image paths
"""
from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv()

driver = GraphDatabase.driver(
    os.getenv('NEO4J_URI'),
    auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
)

# Mapping: node_id -> image_path
SYMBOL_MAPPINGS = {
    'symbol-orzel-blw': 'data/evidence/facebook/BraterstwaLudziWolnych/logo.png',
    'symbol-peace-mir': 'data/evidence/facebook/BraterstwaLudziWolnych/bg_img.png',
}

with driver.session() as session:
    for node_id, image_path in SYMBOL_MAPPINGS.items():
        result = session.run("""
            MATCH (n {id: $id})
            SET n.image = $image
            RETURN n.id, n.name, n.image
        """, id=node_id, image=image_path)
        
        record = result.single()
        if record:
            print(f"✅ Updated {record['n.id']}: {record['n.name']} -> {record['n.image']}")
        else:
            print(f"❌ Node not found: {node_id}")

driver.close()
print("\nDone!")
