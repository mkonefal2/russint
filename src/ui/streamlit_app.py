import streamlit as st
import streamlit.components.v1 as components
import os
import json
import re
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

# --- CONFIGURATION ---
st.set_page_config(layout="wide", page_title="RUSSINT Graph Explorer", initial_sidebar_state="collapsed")
load_dotenv()

# --- CUSTOM CSS ---
st.markdown("""
    <style>
        /* make main content use full width */
        .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0rem !important;
            padding-left: 0rem !important;
            padding-right: 0rem !important;
            max-width: 100% !important;
            margin: 0 auto !important;
        }

        /* Hide the Streamlit left sidebar entirely so the graph area fills the page */
        [data-testid="stSidebar"] {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
        }

        /* Some streamlit versions use different attributes for the sidebar */
        section[aria-label="sidebar"] {
            display: none !important;
            visibility: hidden !important;
            width: 0 !important;
        }

        /* Force the iframe (components.html) to stretch fully */
        iframe {
            width: 100% !important;
            height: 100vh !important;
        }

        /* Remove top header spacing if present */
        header, .css-18e3th9 { display: none !important; }
    </style>
""", unsafe_allow_html=True)

# --- BACKEND: Neo4j Data Fetching ---
def get_neo4j_driver():
    # Try environment variables first, then Streamlit secrets
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    
    # Fallback to st.secrets if available
    if not uri and "NEO4J_URI" in st.secrets:
        uri = st.secrets["NEO4J_URI"]
    if not user and "NEO4J_USER" in st.secrets:
        user = st.secrets["NEO4J_USER"]
    if not password and "NEO4J_PASSWORD" in st.secrets:
        password = st.secrets["NEO4J_PASSWORD"]

    if not uri or not user or not password:
        st.error("Missing credentials! Please set NEO4J_URI, NEO4J_USER, and NEO4J_PASSWORD in Streamlit Secrets.")
        return None
        
    try:
        return GraphDatabase.driver(uri, auth=(user, password))
    except Exception as e:
        st.error(f"Connection failed: {e}")
        return None

@st.cache_data(ttl=60)
def get_graph_data():
    driver = get_neo4j_driver()
    if not driver:
        return None
        
    query = """
    MATCH (n)-[r]->(m)
    RETURN n, r, m
    LIMIT 1000
    """
    
    nodes = {}
    links = []
    
    try:
        with driver.session() as session:
            result = session.run(query)
            for record in result:
                n = record["n"]
                m = record["m"]
                r = record["r"]
                
                def process_node(node):
                    nid = node.element_id if hasattr(node, 'element_id') else str(node.id)
                    if 'id' in node: nid = node['id']
                    props = dict(node)
                    
                    # Label/Group
                    group = list(node.labels)[0] if node.labels else "Unknown"
                    
                    return nid, {
                        "id": nid,
                        "name": node.get("name", node.get("title", "Unknown")),
                        "group": group,
                        "properties": props
                    }

                src_id, src_node = process_node(n)
                tgt_id, tgt_node = process_node(m)
                
                if src_id not in nodes: nodes[src_id] = src_node
                if tgt_id not in nodes: nodes[tgt_id] = tgt_node
                
                links.append({
                    "source": src_id,
                    "target": tgt_id,
                    "type": r.type,
                    "properties": dict(r)
                })
        
        return {"nodes": list(nodes.values()), "links": links}
    except Exception as e:
        st.error(f"Neo4j Error: {e}")
        return {"nodes": [], "links": []}
    finally:
        driver.close()

# --- FRONTEND: Asset Loading & Injection ---
def load_frontend_assets():
    # Assuming this script is in src/ui/
    # Assets are in src/ui/web/
    base_path = Path(__file__).parent / "web"
    
    try:
        with open(base_path / "style.css", "r", encoding="utf-8") as f:
            css = f.read()
            
        with open(base_path / "app.js", "r", encoding="utf-8") as f:
            js = f.read()
            
        return css, js
    except FileNotFoundError:
        st.error("Could not find frontend assets (style.css or app.js) in src/ui/web/")
        return "", ""

def prepare_html(css, js, graph_data):
    # 1. Inject Data
    # We replace the fetch call in app.js with direct data assignment
    
    js_fixed = js.replace(
        "const response = await fetch('/api/graph');",
        "// const response = await fetch('/api/graph');"
    ).replace(
        "if (!response.ok) throw new Error(`Server returned ${response.status} ${response.statusText}`);",
        "// if (!response.ok) ..."
    ).replace(
        "const data = await response.json();",
        "const data = window.graphData;"
    )
    
    # Disable editing save
    js_fixed = js_fixed.replace(
        "const response = await fetch('/api/update_node', {",
        "alert('Editing is disabled in Streamlit view.'); return; const response = await fetch('/api/update_node', {"
    )
    
    # Also disable the status banner for fetch errors since we are injecting
    js_fixed = js_fixed.replace(
        "showStatusBanner('Failed to load graph data. Check console (F12) for details.');",
        "console.warn('Graph init error:', err);"
    )

    # 2. Construct HTML
    html = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <script src="//unpkg.com/force-graph"></script>
        <style>
            {css}
            /* Overrides for Streamlit iframe context */
            body {{ 
                margin: 0; 
                overflow: hidden; 
                background-color: #0d1117; 
                height: 100vh;
            }}
            .container {{
                height: 100vh;
            }}
            #graph-container {{
                width: 100%;
                height: 100%;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div id="graph-container"></div>
            
            <!-- Debug/Control Button -->
            <button onclick="togglePanelVisibility()" style="position: fixed; top: 10px; right: 10px; z-index: 2000; background: #161b22; color: #c9d1d9; border: 1px solid #30363d; padding: 5px 10px; cursor: pointer; pointer-events: auto;">
                👁️ Toggle UI
            </button>

            <div id="details-container" class="collapsed">
                <div id="resize-handle"></div>
                <div class="details-header">
                    <div style="display: flex; align-items: center; gap: 10px;">
                        <button id="toggle-details-btn" onclick="toggleDetailsPanel()" title="Toggle Panel">▼</button>
                        <h2 id="details-title">Select a node</h2>
                    </div>
                    <div class="details-controls">
                        <button id="edit-btn" onclick="toggleEditMode()" style="display:none;">✎ Edit</button>
                        <button id="save-btn" onclick="saveChanges()" style="display:none;">💾 Save</button>
                        <button onclick="resetZoom()">Reset Zoom</button>
                        <button onclick="clearSelection()">Clear Selection</button>
                    </div>
                </div>
                <div class="details-content">
                    <div class="details-table-wrapper">
                        <table id="details-table">
                            <thead>
                                <tr><th style="width: 150px;">Property</th><th>Value</th></tr>
                            </thead>
                            <tbody id="details-body">
                                <tr><td colspan="2" style="text-align:center; color:#555; padding: 20px;">Click on a node to view details</td></tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="details-gallery" id="details-gallery">
                        <div style="color: #555; font-size: 0.8rem;">No evidence selected</div>
                    </div>
                </div>
            </div>
        </div>
        
        <script>
            // Inject Data from Python
            window.graphData = {json.dumps(graph_data)};
            
            // Inject Application Logic
            {js_fixed}
        </script>
    </body>
    </html>
    """
    return html

# --- MAIN APP ---
def main():
    st.title("🕸️ RUSSINT: Kinetic Graph (Streamlit Edition)")
    
    # Sidebar
    with st.sidebar:
        st.header("Connection")
        if not os.getenv("NEO4J_URI"):
            st.warning("Missing NEO4J_URI in .env or secrets.")
        else:
            st.success("Neo4j Configured")
            
        if st.button("Reload Data"):
            st.cache_data.clear()
            st.rerun()
            
        st.markdown("---")
        st.markdown("**Legend**")
        st.markdown("""
        - <span style="color:#f778ba">●</span> Person
        - <span style="color:#58a6ff">●</span> Organization
        - <span style="color:#d2a8ff">●</span> Event
        - <span style="color:#7ee787">●</span> Post
        - <span style="color:#ffa657">●</span> Profile
        - <span style="color:#00bcd4">●</span> Site
        """, unsafe_allow_html=True)

    # Load Data
    with st.spinner("Fetching graph data from Neo4j..."):
        data = get_graph_data()
    
    if not data:
        st.warning("No data found or connection failed.")
        return

    # Load Assets & Render
    css, js = load_frontend_assets()
    if css and js:
        html_content = prepare_html(css, js, data)
        # Increase height to 1000 to prevent clipping on larger screens
        components.html(html_content, height=1000, scrolling=False)

if __name__ == "__main__":
    main()
