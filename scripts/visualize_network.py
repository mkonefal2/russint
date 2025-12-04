"""
RUSSINT - Network Visualization
Wizualizacja sieci powiązań z DuckDB.
"""

import duckdb
from pathlib import Path

# Opcjonalne importy - jeśli nie ma, zainstaluj
try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

try:
    from pyvis.network import Network
    HAS_PYVIS = True
except ImportError:
    HAS_PYVIS = False

# Ścieżki
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "russint.duckdb"
OUTPUT_DIR = DATA_DIR / "visualizations"


def create_network_graph(con):
    """Tworzy graf NetworkX z danych w bazie."""
    if not HAS_NETWORKX:
        print("❌ NetworkX nie jest zainstalowany. Uruchom: pip install networkx")
        return None
    
    G = nx.DiGraph()
    
    # Dodaj węzły (podmioty)
    entities = con.execute("""
        SELECT id, name, entity_type, category 
        FROM entities
    """).fetchall()
    
    for e in entities:
        G.add_node(e[0], label=e[1], entity_type=e[2] or 'unknown', category=e[3] or 'unknown')
    
    # Dodaj krawędzie (relacje)
    relationships = con.execute("""
        SELECT source_id, target_id, relationship_type, confidence, event_name
        FROM relationships
    """).fetchall()
    
    for r in relationships:
        G.add_edge(r[0], r[1], 
                   relationship_type=r[2], 
                   weight=r[3] or 1.0,
                   event=r[4] or '')
    
    return G


def visualize_with_pyvis(G, output_file="network.html"):
    """Tworzy interaktywną wizualizację z Pyvis."""
    if not HAS_PYVIS:
        print("❌ Pyvis nie jest zainstalowany. Uruchom: pip install pyvis")
        return None
    
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Kolory dla typów węzłów
    type_colors = {
        'organization': '#e74c3c',  # czerwony
        'person': '#3498db',        # niebieski
        'profile': '#2ecc71',       # zielony - profil social media
        'page': '#27ae60',          # ciemny zielony
        'group': '#9b59b6',         # fioletowy
        'channel': '#f39c12',       # pomarańczowy
        'event': '#1abc9c',         # turkusowy
        'post': '#f1c40f',          # żółty
        'unknown': '#95a5a6'        # szary
    }
    
    # Kształty/rozmiary dla typów
    type_sizes = {
        'organization': 40,
        'profile': 30,
        'event': 35,
        'post': 20,
        'person': 25,
        'page': 25,
        'group': 30,
        'channel': 25,
        'unknown': 20
    }
    
    # Utwórz sieć Pyvis
    net = Network(
        height="800px", 
        width="100%", 
        bgcolor="#1a1a2e",
        font_color="white",
        directed=True
    )
    
    # Opcje fizyki
    net.barnes_hut(
        gravity=-5000,
        central_gravity=0.3,
        spring_length=200,
        spring_strength=0.05
    )
    
    # Dodaj węzły
    for node_id, data in G.nodes(data=True):
        entity_type = data.get('entity_type', 'unknown')
        color = type_colors.get(entity_type, '#95a5a6')
        size = type_sizes.get(entity_type, 20)
        
        # Kształt węzła w title
        shape_icons = {
            'organization': '🏢',
            'person': '👤',
            'profile': '📱',
            'event': '📅',
            'post': '📝',
            'page': '📄',
            'group': '👥',
            'channel': '📺'
        }
        icon = shape_icons.get(entity_type, '❓')
        
        # Kształty dla różnych typów
        shape_map = {
            'organization': 'dot',
            'person': 'dot',
            'profile': 'box',
            'event': 'diamond',
            'post': 'square',
            'page': 'box',
            'group': 'triangle',
            'channel': 'star'
        }
        
        net.add_node(
            node_id,
            label=data.get('label', node_id),
            color=color,
            size=size,
            title=f"{icon} {entity_type.upper()}\n{data.get('label', node_id)}\nKategoria: {data.get('category', 'N/A')}",
            shape=shape_map.get(entity_type, 'dot')
        )
    
    # Dodaj krawędzie
    for source, target, data in G.edges(data=True):
        rel_type = data.get('relationship_type', 'UNKNOWN')
        event = data.get('event', '')
        
        # Kolory dla typów relacji
        edge_colors = {
            'SPEAKER_AT': '#e74c3c',
            'SPEAKER_AT_EVENT': '#e74c3c',
            'ORGANIZES': '#9b59b6',
            'HAS_PROFILE': '#2ecc71',
            'PUBLISHED': '#3498db',
            'ANNOUNCES': '#1abc9c',
            'REPOSTS': '#f39c12',
            'SHARES_CONTENT_FROM': '#e67e22',
            'MEMBER_OF': '#e91e63',
            'COLLABORATES_WITH': '#00bcd4',
            'MENTIONED_IN': '#ff9800'
        }
        edge_color = edge_colors.get(rel_type, '#cccccc')
        
        net.add_edge(
            source, 
            target, 
            title=f"{rel_type}\n{event}",
            color=edge_color,
            arrows="to"
        )
    
    # Zapisz do HTML
    output_path = OUTPUT_DIR / output_file
    net.save_graph(str(output_path))
    print(f"✅ Zapisano wizualizację: {output_path}")
    
    return output_path


def print_network_stats(G):
    """Wyświetla statystyki grafu."""
    print("\n" + "="*50)
    print("📊 STATYSTYKI SIECI")
    print("="*50)
    
    print(f"📍 Węzły: {G.number_of_nodes()}")
    print(f"🔗 Krawędzie: {G.number_of_edges()}")
    
    # Stopnie węzłów
    in_degrees = dict(G.in_degree())
    out_degrees = dict(G.out_degree())
    
    print("\n🎯 Najwięcej połączeń wychodzących (hubs):")
    for node, degree in sorted(out_degrees.items(), key=lambda x: x[1], reverse=True)[:5]:
        label = G.nodes[node].get('label', node)
        print(f"   {label}: {degree}")
    
    print("\n📥 Najwięcej połączeń przychodzących:")
    for node, degree in sorted(in_degrees.items(), key=lambda x: x[1], reverse=True)[:5]:
        label = G.nodes[node].get('label', node)
        print(f"   {label}: {degree}")


def main():
    print("="*50)
    print("🕸️ RUSSINT - Network Visualization")
    print("="*50)
    
    # Sprawdź zależności
    if not HAS_NETWORKX or not HAS_PYVIS:
        print("\n⚠️ Brakujące zależności:")
        if not HAS_NETWORKX:
            print("   pip install networkx")
        if not HAS_PYVIS:
            print("   pip install pyvis")
        print("\nUruchom: pip install networkx pyvis")
        return
    
    # Połącz z bazą
    con = duckdb.connect(str(DB_PATH), read_only=True)
    
    try:
        # Utwórz graf
        print("\n📊 Tworzenie grafu z bazy danych...")
        G = create_network_graph(con)
        
        if G is None or G.number_of_nodes() == 0:
            print("❌ Brak danych do wizualizacji")
            return
        
        # Statystyki
        print_network_stats(G)
        
        # Wizualizacja
        print("\n🎨 Generowanie wizualizacji...")
        output_path = visualize_with_pyvis(G, "russint_network.html")
        
        if output_path:
            print(f"\n🌐 Otwórz w przeglądarce: {output_path}")
        
    finally:
        con.close()


if __name__ == "__main__":
    main()
