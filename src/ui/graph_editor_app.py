"""
RUSSINT - Graph Editor UI (Streamlit)
Interfejs do ręcznego zarządzania węzłami (entities) i relacjami (relationships)
bez potrzeby edycji kodu. Umożliwia: CRUD na JSON, podgląd grafu, eksport.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
import streamlit as st
import pandas as pd

# Wizualizacja
try:
    import networkx as nx
    from pyvis.network import Network
    HAS_GRAPH = True
except ImportError:
    HAS_GRAPH = False

BASE_DIR = Path(__file__).parent.parent.parent
RAW_DIR = BASE_DIR / "data" / "raw"
INCREMENTS_DIR = BASE_DIR / "data" / "processed" / "graph_increments"
INCREMENTS_DIR.mkdir(parents=True, exist_ok=True)

# Default paths (Global Seed)
GLOBAL_NODES_FILE = RAW_DIR / "graph_nodes.json"
GLOBAL_EDGES_FILE = RAW_DIR / "graph_edges.json"

EXPORT_DIR = BASE_DIR / "data" / "export"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

ENTITY_TYPES = ["organization", "profile", "event", "post", "person"]
REL_TYPES = [
    "HAS_PROFILE", "PUBLISHED", "ANNOUNCES", "ORGANIZES", "SPEAKER_AT", "REPOSTS",
    "SHARES_CONTENT_FROM", "MEMBER_OF", "COLLABORATES_WITH", "MENTIONED_IN"
]

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def load_json(path, default):
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default
    return default


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def get_entity_map(entities):
    return {e["id"]: e for e in entities}

# --------------------------------------------------
# State init
# --------------------------------------------------
st.set_page_config(page_title="RUSSINT Graph Editor", page_icon="🕸️", layout="wide")

# --- DATA SOURCE SELECTOR ---
st.sidebar.title("🕸️ Graph Editor")
data_source = st.sidebar.radio("Źródło danych", ["📂 Pliki Przyrostowe (Increments)", "🌍 Global Seed (Legacy)"])

current_file_path = None
nodes_data = []
edges_data = []

if data_source == "📂 Pliki Przyrostowe (Increments)":
    st.sidebar.info("Edycja pojedynczych plików analizy. To jest zalecany tryb dla dużej skali.")
    files = sorted(list(INCREMENTS_DIR.glob("*.json")), key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not files:
        st.warning("Brak plików w folderze increments.")
        selected_file_name = None
    else:
        file_options = {f.name: f for f in files}
        selected_file_name = st.sidebar.selectbox("Wybierz plik", list(file_options.keys()))
        
        if selected_file_name:
            current_file_path = file_options[selected_file_name]
            data = load_json(current_file_path, {"nodes": [], "edges": []})
            # Obsługa formatu increments (nodes/edges w jednym pliku)
            nodes_data = data.get("nodes", [])
            edges_data = data.get("edges", [])

elif data_source == "🌍 Global Seed (Legacy)":
    st.sidebar.warning("Edycja głównego pliku seed. Uwaga: Przy dużej ilości danych może działać wolno.")
    current_file_path = "GLOBAL" # Marker
    nodes_data = load_json(GLOBAL_NODES_FILE, [])
    edges_data = load_json(GLOBAL_EDGES_FILE, [])

# Load into session state (only if changed or not set)
if "current_source" not in st.session_state or st.session_state.current_source != str(current_file_path):
    st.session_state.entities = nodes_data
    st.session_state.relationships = edges_data
    st.session_state.current_source = str(current_file_path)

# Słowniki do szybkiego lookupu
entity_map = get_entity_map(st.session_state.entities)

# --------------------------------------------------
# Sidebar Navigation
# --------------------------------------------------
page = st.sidebar.radio("Nawigacja", ["📍 Węzły", "🔗 Relacje", "🌐 Graf", "💾 Zapisz"])  
st.sidebar.markdown("---")
st.sidebar.markdown(f"**Węzły:** {len(st.session_state.entities)}")
st.sidebar.markdown(f"**Relacje:** {len(st.session_state.relationships)}")

# --------------------------------------------------
# Save Logic
# --------------------------------------------------
if page == "💾 Zapisz":
    st.header("💾 Zapisz zmiany")
    st.info(f"Aktualne źródło: {data_source}")
    if current_file_path:
        st.code(str(current_file_path))
    
    if st.button("Zapisz zmiany na dysku"):
        if data_source == "📂 Pliki Przyrostowe (Increments)" and current_file_path:
            # Save back to increment format
            output_data = {
                "meta": {
                    "updated_at": datetime.now().isoformat(),
                    "source": "Graph Editor UI"
                },
                "nodes": st.session_state.entities,
                "edges": st.session_state.relationships
            }
            save_json(current_file_path, output_data)
            st.success(f"Zapisano plik: {current_file_path.name}")
            
        elif data_source == "🌍 Global Seed (Legacy)":
            save_json(GLOBAL_NODES_FILE, st.session_state.entities)
            save_json(GLOBAL_EDGES_FILE, st.session_state.relationships)
            st.success("Zapisano pliki Global Seed (nodes + edges).")

# --------------------------------------------------
# Page: Entities CRUD
# --------------------------------------------------
if page == "📍 Węzły":
    st.header("📍 Zarządzanie węzłami (entities)")
    with st.expander("➕ Dodaj nowy węzeł", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_type = st.selectbox("Typ", ENTITY_TYPES)
        with col2:
            new_name = st.text_input("Nazwa")
        with col3:
            new_country = st.text_input("Kraj", value="PL")
        url = st.text_input("URL / Link (opcjonalnie)")
        description = st.text_area("Opis", height=120)
        parent_org = None
        if new_type == "profile":
            parent_org = st.selectbox("Organizacja nadrzędna", ["(brak)"] + [e["id"] for e in st.session_state.entities if e["entity_type"] == "organization"])
            if parent_org == "(brak)":
                parent_org = None
        if st.button("💾 Zapisz węzeł", type="primary"):
            if not new_name.strip():
                st.error("Nazwa jest wymagana")
            else:
                new_id = generate_id({
                    "organization": "org",
                    "profile": "profile",
                    "event": "evt",
                    "post": "post",
                    "person": "ent"
                }.get(new_type, "node"))
                data = {
                    "id": new_id,
                    "name": new_name.strip(),
                    "entity_type": new_type,
                    "description": description.strip(),
                    "country": new_country.strip(),
                    "first_seen": datetime.utcnow().date().isoformat(),
                }
                if url:
                    data["url"] = url.strip()
                if new_type == "profile" and parent_org:
                    data["parent_org_id"] = parent_org
                st.session_state.entities.append(data)
                
                if data_source == "🌍 Global Seed (Legacy)":
                    save_json(GLOBAL_NODES_FILE, st.session_state.entities)
                
                st.success(f"Dodano węzeł {new_name} ({new_id}) (w pamięci)")
                st.experimental_rerun()

    st.markdown("### 🔍 Filtruj")
    f_type = st.multiselect("Filtr typów", ENTITY_TYPES, default=ENTITY_TYPES)
    filtered = [e for e in st.session_state.entities if e["entity_type"] in f_type]
    st.dataframe(pd.DataFrame(filtered), use_container_width=True)

    st.markdown("### ✏️ Edycja / Usuwanie")
    edit_id = st.selectbox("Wybierz węzeł", ["--"] + [e["id"] for e in filtered])
    if edit_id != "--":
        ent = entity_map.get(edit_id)
        if ent:
            new_name2 = st.text_input("Nazwa (edycja)", value=ent.get("name", ""))
            new_desc2 = st.text_area("Opis (edycja)", value=ent.get("description", ""), height=100)
            new_country2 = st.text_input("Kraj (edycja)", value=ent.get("country", ""))
            if st.button("💾 Zapisz zmiany"):
                ent["name"] = new_name2.strip()
                ent["description"] = new_desc2.strip()
                ent["country"] = new_country2.strip()
                # Save logic handled by "Save" page now, but for UX we can update session state
                # and optionally save if in Global mode, but better to rely on the main Save button
                # to avoid confusion with Incremental mode.
                # However, users expect immediate save.
                # Let's use the generic save logic.
                if data_source == "🌍 Global Seed (Legacy)":
                    save_json(GLOBAL_NODES_FILE, st.session_state.entities)
                st.success("Zaktualizowano w pamięci. Przejdź do zakładki 'Zapisz' aby utrwalić zmiany w pliku.")
                st.experimental_rerun()
            if st.button("🗑️ Usuń węzeł", type="secondary"):
                # Usuń powiązane relacje
                st.session_state.relationships = [r for r in st.session_state.relationships if r["source_id"] != edit_id and r["target_id"] != edit_id]
                st.session_state.entities = [e for e in st.session_state.entities if e["id"] != edit_id]
                
                if data_source == "🌍 Global Seed (Legacy)":
                    save_json(GLOBAL_NODES_FILE, st.session_state.entities)
                    save_json(GLOBAL_EDGES_FILE, st.session_state.relationships)
                
                st.warning("Usunięto węzeł i powiązane relacje (w pamięci).")
                st.experimental_rerun()

# --------------------------------------------------
# Page: Relationships CRUD
# --------------------------------------------------
elif page == "🔗 Relacje":
    st.header("🔗 Zarządzanie relacjami")
    with st.expander("➕ Dodaj nową relację", expanded=True):
        col1, col2 = st.columns(2)
        # Filter entities for dropdowns
        entity_ids = [e["id"] for e in st.session_state.entities]
        
        with col1:
            src = st.selectbox("Źródło", entity_ids)
        with col2:
            tgt = st.selectbox("Cel", entity_ids)
        r_type = st.selectbox("Typ relacji", REL_TYPES)
        date_val = st.date_input("Data obserwacji", datetime.utcnow().date())
        evidence = st.text_input("Dowód / Źródło")
        confidence = st.slider("Pewność", 0.0, 1.0, 1.0, 0.05)
        if st.button("💾 Dodaj relację", type="primary"):
            if src == tgt:
                st.error("Źródło i cel nie mogą być identyczne")
            else:
                rid = generate_id("rel")
                st.session_state.relationships.append({
                    "id": rid,
                    "source_id": src,
                    "source_name": entity_map.get(src, {}).get("name", src),
                    "target_id": tgt,
                    "target_name": entity_map.get(tgt, {}).get("name", tgt),
                    "relationship_type": r_type,
                    "date": date_val.isoformat(),
                    "confidence": confidence,
                    "evidence": evidence.strip()
                })
                if data_source == "🌍 Global Seed (Legacy)":
                    save_json(GLOBAL_EDGES_FILE, st.session_state.relationships)
                st.success(f"Dodano relację {rid} (w pamięci).")
                st.experimental_rerun()

    st.markdown("### 🔍 Filtruj relacje")
    f_rel_types = st.multiselect("Typy", REL_TYPES, default=REL_TYPES)
    rel_df = [r for r in st.session_state.relationships if r["relationship_type"] in f_rel_types]
    st.dataframe(pd.DataFrame(rel_df), use_container_width=True)

    st.markdown("### 🗑️ Usuń relację")
    del_id = st.selectbox("Relacja", ["--"] + [r["id"] for r in rel_df])
    if del_id != "--":
        if st.button("Usuń wybraną relację"):
            st.session_state.relationships = [r for r in st.session_state.relationships if r["id"] != del_id]
            if data_source == "🌍 Global Seed (Legacy)":
                save_json(GLOBAL_EDGES_FILE, st.session_state.relationships)
            st.warning("Usunięto relację (w pamięci).")
            st.experimental_rerun()

# --------------------------------------------------
# Page: Graph visualization
# --------------------------------------------------
elif page == "🌐 Graf":
    st.header("🌐 Podgląd grafu")
    if not HAS_GRAPH:
        st.error("Brak pakietów networkx/pyvis. Zainstaluj: pip install networkx pyvis")
    else:
        # Budowa grafu
        G = nx.DiGraph()
        for e in st.session_state.entities:
            G.add_node(e["id"], label=e.get("name"), type=e.get("entity_type"))
        for r in st.session_state.relationships:
            G.add_edge(r["source_id"], r["target_id"], type=r["relationship_type"], label=r["relationship_type"], evidence=r.get("evidence"))
        # Pyvis
        net = Network(height="700px", width="100%", bgcolor="#111", font_color="white", directed=True)
        net.barnes_hut(gravity=-4000, central_gravity=0.3, spring_length=180, spring_strength=0.05)
        type_colors = {
            "organization": "#e74c3c", "profile": "#2ecc71", "event": "#1abc9c", "post": "#f1c40f", "person": "#3498db"
        }
        for n, data in G.nodes(data=True):
            net.add_node(n, label=data.get("label"), color=type_colors.get(data.get("type"), "#95a5a6"), title=f"{data.get('type')}\n{data.get('label')}")
        edge_colors = {
            "HAS_PROFILE": "#2ecc71", "PUBLISHED": "#3498db", "ANNOUNCES": "#1abc9c", "ORGANIZES": "#9b59b6", "SPEAKER_AT": "#e74c3c"
        }
        for a, b, data in G.edges(data=True):
            net.add_edge(a, b, title=f"{data.get('type')}\n{data.get('evidence','')}", color=edge_colors.get(data.get('type'), "#cccccc"), arrows="to")
        net.show(str(EXPORT_DIR / "_temp_graph.html"))
        html = (EXPORT_DIR / "_temp_graph.html").read_text(encoding="utf-8")
        st.components.v1.html(html, height=720, scrolling=True)

        st.markdown("---")
        st.subheader("📊 Statystyki")
        st.write(f"Węzły: {G.number_of_nodes()} | Relacje: {G.number_of_edges()}")
        deg_out = sorted(G.out_degree(), key=lambda x: x[1], reverse=True)[:10]
        st.write("Top wyjściowych:", deg_out)
        deg_in = sorted(G.in_degree(), key=lambda x: x[1], reverse=True)[:10]
        st.write("Top przychodzących:", deg_in)

# --------------------------------------------------
# Page: Export
# --------------------------------------------------
elif page == "📤 Eksport":
    st.header("📤 Eksport danych")
    # CSV nodes
    nodes_csv = "Id,Label,Type\n" + "".join([f"{e['id']},{e['name']},{e['entity_type']}\n" for e in st.session_state.entities])
    edges_csv = "Source,Target,Type,Confidence\n" + "".join([
        f"{r['source_id']},{r['target_id']},{r['relationship_type']},{r.get('confidence',1.0)}\n" for r in st.session_state.relationships
    ])
    st.download_button("⬇️ Węzły (CSV)", nodes_csv, file_name="nodes.csv")
    st.download_button("⬇️ Relacje (CSV)", edges_csv, file_name="edges.csv")
    st.download_button("⬇️ entities.json", json.dumps(st.session_state.entities, ensure_ascii=False, indent=2), file_name="entities.json")
    st.download_button("⬇️ relationships.json", json.dumps(st.session_state.relationships, ensure_ascii=False, indent=2), file_name="relationships.json")

    st.markdown("---")
    st.subheader("🔄 Synchronizacja plików")
    if st.button("💾 Zapisz bieżący stan do JSON"):
        save_json(ENTITIES_FILE, st.session_state.entities)
        save_json(REL_FILE, st.session_state.relationships)
        st.success("Zapisano JSON")

    st.info("Do uruchomienia: streamlit run src/ui/graph_editor_app.py")

