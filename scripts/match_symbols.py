"""
Symbol Matcher - automatyczne dopasowywanie symboli/grafik do node'ów

Ten skrypt:
1. Skanuje folder data/evidence/symbols/ w poszukiwaniu plików graficznych
2. Próbuje dopasować je do istniejących node'ów typu 'symbol' w Neo4j
3. Aktualizuje pole 'image' w node'ach z dopasowaną ścieżką

Konwencja nazewnictwa plików:
- symbol-orzel-blw.png -> node id: symbol-orzel-blw
- peace-pokoj-mir.jpg -> node id: symbol-peace-mir (fuzzy match)
"""

import os
import re
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv
from difflib import SequenceMatcher

load_dotenv()

SYMBOLS_DIR = Path("data/evidence/symbols")
SUPPORTED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg'}


def get_driver():
    return GraphDatabase.driver(
        os.getenv('NEO4J_URI'),
        auth=(os.getenv('NEO4J_USER'), os.getenv('NEO4J_PASSWORD'))
    )


def normalize_name(name: str) -> str:
    """Normalize name for matching: lowercase, remove special chars"""
    name = name.lower()
    name = re.sub(r'[^a-z0-9ąćęłńóśźżа-яё]', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def similarity(a: str, b: str) -> float:
    """Calculate similarity ratio between two strings"""
    return SequenceMatcher(None, normalize_name(a), normalize_name(b)).ratio()


def get_symbol_nodes(driver):
    """Fetch all symbol nodes from Neo4j"""
    with driver.session() as session:
        result = session.run("""
            MATCH (n)
            WHERE n.entity_type = 'symbol' 
               OR n.name CONTAINS 'Logo' 
               OR n.name CONTAINS 'Grafika'
               OR n.name CONTAINS 'Symbol'
            RETURN n.id as id, n.name as name, n.image as image
        """)
        return [dict(r) for r in result]


def find_symbol_files():
    """Find all symbol files in the symbols directory"""
    if not SYMBOLS_DIR.exists():
        print(f"⚠️ Folder {SYMBOLS_DIR} nie istnieje")
        return []
    
    files = []
    for f in SYMBOLS_DIR.iterdir():
        if f.suffix.lower() in SUPPORTED_EXTENSIONS:
            files.append(f)
    return files


def match_file_to_node(file_path: Path, nodes: list) -> tuple:
    """
    Try to match a file to a node using various strategies:
    1. Exact ID match (filename without extension == node id)
    2. Fuzzy name matching
    """
    filename = file_path.stem  # filename without extension
    
    # Strategy 1: Exact ID match
    for node in nodes:
        if node['id'] == filename:
            return node, 1.0
    
    # Strategy 2: Fuzzy match on ID
    best_match = None
    best_score = 0.0
    
    for node in nodes:
        # Match against node ID
        score_id = similarity(filename, node['id'])
        # Match against node name
        score_name = similarity(filename, node['name'])
        
        score = max(score_id, score_name)
        
        if score > best_score and score > 0.5:  # Threshold
            best_score = score
            best_match = node
    
    return best_match, best_score


def update_node_image(driver, node_id: str, image_path: str):
    """Update the image field of a node in Neo4j"""
    with driver.session() as session:
        session.run("""
            MATCH (n {id: $id})
            SET n.image = $image
        """, id=node_id, image=image_path)


def main():
    print("="*50)
    print("🖼️  RUSSINT Symbol Matcher")
    print("="*50)
    
    driver = get_driver()
    
    # Get existing symbol nodes
    nodes = get_symbol_nodes(driver)
    print(f"\n📊 Znaleziono {len(nodes)} node'ów typu symbol w bazie:")
    for n in nodes:
        img = n.get('image', 'brak')
        print(f"   - {n['id']}: {n['name']} [image: {img}]")
    
    # Find symbol files
    files = find_symbol_files()
    print(f"\n📁 Znaleziono {len(files)} plików w {SYMBOLS_DIR}:")
    for f in files:
        print(f"   - {f.name}")
    
    if not files:
        print("\n💡 Aby dodać symbole, umieść pliki graficzne w folderze:")
        print(f"   {SYMBOLS_DIR.absolute()}")
        print("\n   Nazwy plików powinny odpowiadać ID node'ów, np.:")
        print("   - symbol-orzel-blw.png")
        print("   - symbol-peace-mir.jpg")
        driver.close()
        return
    
    # Match files to nodes
    print("\n🔗 Dopasowywanie plików do node'ów:")
    matches = []
    
    for file_path in files:
        node, score = match_file_to_node(file_path, nodes)
        
        if node:
            rel_path = f"data/evidence/symbols/{file_path.name}"
            print(f"   ✅ {file_path.name} → {node['id']} (score: {score:.2f})")
            matches.append((node['id'], rel_path))
        else:
            print(f"   ❌ {file_path.name} → brak dopasowania")
    
    # Update database
    if matches:
        print(f"\n💾 Aktualizuję {len(matches)} node'ów w Neo4j...")
        for node_id, image_path in matches:
            update_node_image(driver, node_id, image_path)
            print(f"   Updated {node_id} → {image_path}")
        print("✅ Zakończono!")
    
    driver.close()


if __name__ == "__main__":
    main()
