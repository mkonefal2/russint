"""
RUSSINT - Neo4j Graph Editor UI (Streamlit)
Interfejs do zarządzania grafem w Neo4j z podglądem i CRUD.
"""

import streamlit as st
from neo4j import GraphDatabase
import pandas as pd
from datetime import datetime
import uuid
import os

# Załaduj zmienne z .env jeśli istnieje
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Konfiguracja Neo4j Aura - użyj zmiennych środowiskowych lub wartości domyślnych
NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://1f589f65.databases.neo4j.io")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "YOUR_PASSWORD_HERE")

ENTITY_TYPES = ["organization", "profile", "event", "post", "person"]
REL_TYPES = [
    "HAS_PROFILE", "PUBLISHED", "ANNOUNCES", "ORGANIZES", "SPEAKER_AT", "REPOSTS",
    "SHARES_CONTENT_FROM", "MEMBER_OF", "COLLABORATES_WITH", "MENTIONED_IN"
]

st.set_page_config(page_title="RUSSINT Neo4j Editor", page_icon="🕸️", layout="wide")

# Sprawdź hasło
if NEO4J_PASSWORD == "YOUR_PASSWORD_HERE":
    st.error("⚠️ Nie ustawiono hasła Neo4j!")
    st.info("Ustaw zmienną środowiskową przed uruchomieniem:")
    st.code("$env:NEO4J_PASSWORD='twoje_haslo'\nstreamlit run src/ui/neo4j_editor_app.py")
    st.stop()

# Połączenie z Neo4j
@st.cache_resource
def get_neo4j_driver():
    try:
        return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    except Exception as e:
        st.error(f"Błąd połączenia z Neo4j: {e}")
        st.stop()

driver = get_neo4j_driver()

# Helpers
def run_query(query, **params):
    with driver.session() as session:
        result = session.run(query, **params)
        return [record.data() for record in result]

def generate_id(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:8]}"

# Sidebar
st.sidebar.title("🕸️ Neo4j Graph Editor")
page = st.sidebar.radio("Nawigacja", ["📍 Węzły", "🔗 Relacje", "🌐 Zapytania", "📊 Statystyki"])

# Pobierz statystyki
try:
    node_count = run_query("MATCH (n) RETURN count(n) as c")[0]['c']
    rel_count = run_query("MATCH ()-[r]->() RETURN count(r) as c")[0]['c']
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Węzły:** {node_count}")
    st.sidebar.markdown(f"**Relacje:** {rel_count}")
except Exception as e:
    st.sidebar.error(f"Błąd połączenia: {e}")
    st.stop()

# --------------------------------------------------
# Page: Nodes
# --------------------------------------------------
if page == "📍 Węzły":
    st.header("📍 Zarządzanie węzłami")
    
    with st.expander("➕ Dodaj nowy węzeł", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            new_type = st.selectbox("Typ", ENTITY_TYPES)
        with col2:
            new_name = st.text_input("Nazwa")
        with col3:
            new_country = st.text_input("Kraj", value="PL")
        
        url = st.text_input("URL (opcjonalnie)")
        description = st.text_area("Opis", height=100)
        
        if st.button("💾 Dodaj węzeł", type="primary"):
            if not new_name.strip():
                st.error("Nazwa jest wymagana")
            else:
                new_id = generate_id({
                    "organization": "org",
                    "profile": "profile",
                    "event": "evt",
                    "post": "post",
                    "person": "ent"
                }[new_type])
                
                label_map = {
                    'organization': 'Organization',
                    'person': 'Person',
                    'profile': 'Profile',
                    'event': 'Event',
                    'post': 'Post'
                }
                label = label_map.get(new_type, 'Entity')
                
                query = f"""
                CREATE (n:{label}:Entity {{
                    id: $id,
                    name: $name,
                    entity_type: $type,
                    description: $desc,
                    country: $country,
                    url: $url,
                    first_seen: $date
                }})
                RETURN n
                """
                run_query(query, 
                    id=new_id, 
                    name=new_name.strip(),
                    type=new_type,
                    desc=description.strip(),
                    country=new_country.strip(),
                    url=url.strip(),
                    date=datetime.utcnow().date().isoformat()
                )
                st.success(f"✅ Dodano {new_name} ({new_id})")
                st.rerun()
    
    st.markdown("### 🔍 Przegląd węzłów")
    f_type = st.multiselect("Filtr typu", ENTITY_TYPES, default=ENTITY_TYPES)
    
    query = """
    MATCH (n:Entity)
    WHERE n.entity_type IN $types
    RETURN n.id as id, n.name as name, n.entity_type as type, 
           n.country as country, n.description as description
    ORDER BY n.name
    LIMIT 100
    """
    nodes = run_query(query, types=f_type)
    if nodes:
        df = pd.DataFrame(nodes)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Brak węzłów")
    
    st.markdown("### 🗑️ Usuń węzeł")
    if nodes:
        del_id = st.selectbox("Wybierz węzeł", ["--"] + [n['id'] for n in nodes])
        if del_id != "--":
            if st.button("Usuń węzeł i powiązania"):
                run_query("MATCH (n:Entity {id: $id}) DETACH DELETE n", id=del_id)
                st.warning("Usunięto węzeł")
                st.rerun()

# --------------------------------------------------
# Page: Relationships
# --------------------------------------------------
elif page == "🔗 Relacje":
    st.header("🔗 Zarządzanie relacjami")
    
    # Pobierz listę węzłów
    all_nodes = run_query("MATCH (n:Entity) RETURN n.id as id, n.name as name ORDER BY n.name")
    node_map = {n['id']: n['name'] for n in all_nodes}
    
    with st.expander("➕ Dodaj relację", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            src = st.selectbox("Źródło", list(node_map.keys()), format_func=lambda x: f"{node_map[x]} ({x})")
        with col2:
            tgt = st.selectbox("Cel", list(node_map.keys()), format_func=lambda x: f"{node_map[x]} ({x})")
        
        r_type = st.selectbox("Typ relacji", REL_TYPES)
        date_val = st.date_input("Data", datetime.utcnow().date())
        evidence = st.text_input("Dowód")
        confidence = st.slider("Pewność", 0.0, 1.0, 1.0, 0.05)
        
        if st.button("💾 Dodaj relację", type="primary"):
            if src == tgt:
                st.error("Źródło i cel nie mogą być identyczne")
            else:
                query = f"""
                MATCH (a:Entity {{id: $src}})
                MATCH (b:Entity {{id: $tgt}})
                MERGE (a)-[r:{r_type}]->(b)
                SET r.date = $date,
                    r.confidence = $conf,
                    r.evidence = $evidence,
                    r.source_name = a.name,
                    r.target_name = b.name
                RETURN r
                """
                run_query(query, src=src, tgt=tgt, date=date_val.isoformat(), conf=confidence, evidence=evidence)
                st.success("✅ Dodano relację")
                st.rerun()
    
    st.markdown("### 🔍 Przegląd relacji")
    query = """
    MATCH (a)-[r]->(b)
    RETURN a.name as source, type(r) as type, b.name as target, 
           r.date as date, r.confidence as confidence, r.evidence as evidence
    ORDER BY r.date DESC
    LIMIT 100
    """
    rels = run_query(query)
    if rels:
        st.dataframe(pd.DataFrame(rels), use_container_width=True)
    else:
        st.info("Brak relacji")

# --------------------------------------------------
# Page: Queries
# --------------------------------------------------
elif page == "🌐 Zapytania":
    st.header("🌐 Zapytania Cypher")
    
    examples = {
        "Wszystko": "MATCH (n)-[r]->(m) RETURN n, r, m LIMIT 50",
        "Organizacje i profile": "MATCH (o:Organization)-[:HAS_PROFILE]->(p:Profile) RETURN o, p",
        "Wydarzenia i prelegenci": "MATCH (e:Event)<-[:SPEAKER_AT]-(p:Person) RETURN e.name as Event, collect(p.name) as Speakers",
        "Ścieżki 1-3 kroki": "MATCH path = (a)-[*1..3]-(b) RETURN path LIMIT 20",
        "Top węzły": "MATCH (n) OPTIONAL MATCH (n)-[r]->() WITH n, count(r) as d RETURN n.name, d ORDER BY d DESC LIMIT 10"
    }
    
    example = st.selectbox("Przykładowe zapytania", list(examples.keys()))
    query = st.text_area("Zapytanie Cypher", value=examples[example], height=150)
    
    if st.button("🚀 Wykonaj", type="primary"):
        try:
            results = run_query(query)
            if results:
                st.success(f"Zwrócono {len(results)} wyników")
                st.json(results[:50])  # Max 50 dla czytelności
            else:
                st.info("Brak wyników")
        except Exception as e:
            st.error(f"Błąd: {e}")

# --------------------------------------------------
# Page: Stats
# --------------------------------------------------
elif page == "📊 Statystyki":
    st.header("📊 Statystyki grafu")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Węzły wg typu")
        query = "MATCH (n:Entity) RETURN n.entity_type as type, count(*) as count ORDER BY count DESC"
        data = run_query(query)
        if data:
            df = pd.DataFrame(data)
            st.bar_chart(df.set_index('type'))
    
    with col2:
        st.subheader("Relacje wg typu")
        query = "MATCH ()-[r]->() RETURN type(r) as type, count(*) as count ORDER BY count DESC"
        data = run_query(query)
        if data:
            df = pd.DataFrame(data)
            st.bar_chart(df.set_index('type'))
    
    st.subheader("🎯 Top węzły (stopień wychodzący)")
    query = """
    MATCH (n:Entity)
    OPTIONAL MATCH (n)-[r]->()
    WITH n, count(r) as degree
    RETURN n.name as name, n.entity_type as type, degree
    ORDER BY degree DESC
    LIMIT 10
    """
    data = run_query(query)
    if data:
        st.table(pd.DataFrame(data))
    
    st.subheader("🌐 Neo4j Browser")
    st.markdown("Otwórz [http://localhost:7474](http://localhost:7474) dla pełnej wizualizacji")
