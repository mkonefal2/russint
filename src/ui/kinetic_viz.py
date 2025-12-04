import streamlit as st
import os
from neo4j import GraphDatabase
import json
import streamlit.components.v1 as components
from dotenv import load_dotenv
import threading
import http.server
import socketserver
from pathlib import Path

# Load environment variables
load_dotenv()

# --- IMAGE SERVER SETUP ---
# Uruchamiamy prosty serwer HTTP w tle, aby serwować pliki z folderu data/
# Jest to konieczne, aby komponent JS mógł wyświetlać lokalne obrazki.
PORT = 8000
DATA_DIR = Path(__file__).parent.parent.parent / "data"

def start_image_server():
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(DATA_DIR), **kwargs)
            
    # Sprawdź czy port jest zajęty
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', PORT))
    sock.close()
    
    if result != 0: # Port jest wolny
        try:
            with socketserver.TCPServer(("", PORT), Handler) as httpd:
                print(f"Serving data at port {PORT}")
                httpd.serve_forever()
        except OSError:
            pass # Port mógł zostać zajęty w międzyczasie

# Uruchom serwer w osobnym wątku (daemon), jeśli jeszcze nie działa
if 'server_started' not in st.session_state:
    server_thread = threading.Thread(target=start_image_server, daemon=True)
    server_thread.start()
    st.session_state['server_started'] = True

# --- APP CONFIG ---
st.set_page_config(
    page_title="RUSSINT Kinetic Graph",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Styles matching SQL.html
st.markdown("""
<style>
    .stApp {
        background-color: #0d1117;
    }
    h1, h2, h3, p, div, span {
        color: #c9d1d9 !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stSidebar {
        background-color: #161b22;
        border-right: 1px solid #30363d;
    }
    /* Custom Button Style */
    .stButton > button {
        background: transparent;
        border: 1px solid #58a6ff;
        color: #58a6ff;
        border-radius: 20px;
        transition: 0.2s;
    }
    .stButton > button:hover {
        background: #58a6ff;
        color: #fff;
        border-color: #58a6ff;
    }
</style>
""", unsafe_allow_html=True)

# Neo4j Connection
def get_driver():
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    if not uri or not user or not password:
        return None
    return GraphDatabase.driver(uri, auth=(user, password))

class Neo4jEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        return super().default(obj)

def get_graph_data(limit=100):
    driver = get_driver()
    if not driver:
        return None
    
    query = """
    MATCH (n)-[r]->(m)
    RETURN n, r, m
    LIMIT $limit
    """
    
    nodes = {}
    links = []
    
    with driver.session() as session:
        result = session.run(query, limit=limit)
        for record in result:
            n = record["n"]
            m = record["m"]
            r = record["r"]
            
            # Helper to process node
            def process_node(node_obj):
                n_id = node_obj.element_id if hasattr(node_obj, 'element_id') else str(node_obj.id)
                if 'id' in node_obj:
                    n_id = node_obj['id']
                
                props = dict(node_obj)
                
                # Fix screenshot path if exists
                # Zakładamy, że w bazie ścieżka jest np. "data/evidence/..." lub "evidence/..."
                # Serwer HTTP serwuje zawartość folderu "data", więc URL to http://localhost:8000/evidence/...
                if 'screenshot' in props:
                    raw_path = props['screenshot']
                    # Usuń 'data/' z początku jeśli jest, bo root serwera to data/
                    if raw_path.startswith('data/'):
                        props['screenshot_url'] = f"http://localhost:{PORT}/{raw_path[5:]}"
                    elif raw_path.startswith('data\\'):
                        props['screenshot_url'] = f"http://localhost:{PORT}/{raw_path[5:].replace(os.sep, '/')}"
                    else:
                        props['screenshot_url'] = f"http://localhost:{PORT}/{raw_path}"
                
                return n_id, {
                    "id": n_id,
                    "name": node_obj.get("name", node_obj.get("title", "Unknown")),
                    "group": list(node_obj.labels)[0] if node_obj.labels else "Unknown",
                    "properties": props
                }

            src_id, src_node = process_node(n)
            tgt_id, tgt_node = process_node(m)
            
            if src_id not in nodes: nodes[src_id] = src_node
            if tgt_id not in nodes: nodes[tgt_id] = tgt_node
            
            # Process Relationship
            links.append({
                "source": src_id,
                "target": tgt_id,
                "type": r.type,
                "properties": dict(r)
            })
            
    driver.close()
    return {"nodes": list(nodes.values()), "links": links}

# Sidebar
with st.sidebar:
    st.title("⚙️ Config")
    limit = st.slider("Max Relationships", 10, 500, 100)
    refresh = st.button("Refresh Data")
    st.info(f"Image Server running on port {PORT}")

# Main Content
st.title("KINETIC GRAPH VISUALIZER")
st.markdown("<small style='color: #8b949e;'>Neo4j Database Visualization • Click nodes for details</small>", unsafe_allow_html=True)

# Fetch Data
data = get_graph_data(limit)

if not data:
    st.error("Could not connect to Neo4j. Please check your .env file.")
else:
    # Serialize data with custom encoder
    json_data = json.dumps(data, cls=Neo4jEncoder)

    # HTML/JS Component
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ margin: 0; background-color: #0d1117; overflow: hidden; font-family: 'Segoe UI', sans-serif; }}
            
            /* Tooltip */
            .graph-tooltip {{
                background: #161b22 !important;
                border: 1px solid #58a6ff !important;
                color: #c9d1d9 !important;
                padding: 8px !important;
                border-radius: 4px !important;
                box-shadow: 0 4px 15px rgba(0,0,0,0.5);
            }}

            /* Details Panel (Slide-in) */
            #details-panel {{
                position: fixed;
                top: 0;
                right: -450px; /* Hidden initially */
                width: 400px;
                height: 100vh;
                background: rgba(22, 27, 34, 0.95);
                border-left: 1px solid #30363d;
                box-shadow: -10px 0 30px rgba(0,0,0,0.5);
                transition: right 0.3s cubic-bezier(0.4, 0, 0.2, 1);
                z-index: 1000;
                padding: 20px;
                overflow-y: auto;
                backdrop-filter: blur(10px);
                color: #c9d1d9;
            }}

            #details-panel.open {{
                right: 0;
            }}

            .panel-header {{
                border-bottom: 1px solid #30363d;
                padding-bottom: 15px;
                margin-bottom: 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}

            .panel-title {{
                margin: 0;
                font-size: 1.4rem;
                color: #58a6ff;
            }}

            .close-btn {{
                background: none;
                border: none;
                color: #8b949e;
                cursor: pointer;
                font-size: 1.2rem;
            }}
            .close-btn:hover {{ color: #fff; }}

            /* Data Table */
            .prop-table {{
                width: 100%;
                border-collapse: collapse;
                font-size: 0.9rem;
                margin-bottom: 20px;
            }}
            .prop-table td {{
                padding: 8px 0;
                border-bottom: 1px solid rgba(48, 54, 61, 0.5);
                vertical-align: top;
            }}
            .prop-key {{
                color: #8b949e;
                width: 100px;
                font-weight: 600;
            }}
            .prop-val {{
                color: #c9d1d9;
                word-break: break-word;
            }}

            /* Gallery */
            .gallery-container {{
                margin-top: 20px;
            }}
            .gallery-img {{
                width: 100%;
                border-radius: 6px;
                border: 1px solid #30363d;
                margin-bottom: 10px;
                transition: transform 0.2s;
            }}
            .gallery-img:hover {{
                transform: scale(1.02);
                border-color: #58a6ff;
            }}
            
            .section-header {{
                text-transform: uppercase;
                font-size: 0.75rem;
                letter-spacing: 1px;
                color: #f778ba;
                margin-bottom: 10px;
                margin-top: 20px;
            }}

        </style>
        <script src="//unpkg.com/force-graph"></script>
    </head>
    <body>
        <div id="graph"></div>
        
        <!-- Details Panel -->
        <div id="details-panel">
            <div class="panel-header">
                <h2 class="panel-title" id="panel-title">Details</h2>
                <button class="close-btn" onclick="closePanel()">✕</button>
            </div>
            <div id="panel-content">
                <!-- Content injected by JS -->
            </div>
        </div>

        <script>
            const gData = {json_data};
            
            // Color palette matching SQL.html
            const colors = {{
                'Person': '#f778ba',      // Pink
                'Organization': '#58a6ff', // Blue
                'Event': '#d2a8ff',       // Purple
                'Post': '#7ee787',        // Green
                'Profile': '#ffa657',     // Orange
                'default': '#8b949e'      // Grey
            }};

            const Graph = ForceGraph()
                (document.getElementById('graph'))
                .graphData(gData)
                .backgroundColor('#0d1117')
                .nodeId('id')
                .nodeLabel('name')
                .nodeRelSize(6)
                .linkColor(() => 'rgba(88, 166, 255, 0.15)')
                .linkWidth(1)
                .linkDirectionalParticles(2)
                .linkDirectionalParticleWidth(2)
                .linkDirectionalParticleSpeed(0.005)
                .linkDirectionalParticleColor(() => '#58a6ff')
                .nodeCanvasObject((node, ctx, globalScale) => {{
                    const label = node.name;
                    const fontSize = 12/globalScale;
                    ctx.font = `${{fontSize}}px 'Segoe UI', Sans-Serif`;
                    const textWidth = ctx.measureText(label).width;
                    const bckgDimensions = [textWidth + fontSize, fontSize * 1.4];
                    
                    // Node Color based on group
                    const color = colors[node.group] || colors['default'];

                    // Draw "Card" background (like SQL rows)
                    ctx.fillStyle = 'rgba(22, 27, 34, 0.9)'; // #161b22 with opacity
                    ctx.strokeStyle = color;
                    ctx.lineWidth = 1 / globalScale;
                    
                    // Glow effect
                    if (node === window.selectedNode) {{
                        ctx.shadowColor = '#fff';
                        ctx.shadowBlur = 15;
                        ctx.strokeStyle = '#fff';
                    }} else {{
                        ctx.shadowColor = color;
                        ctx.shadowBlur = 5;
                    }}
                    
                    ctx.beginPath();
                    ctx.roundRect(
                        node.x - bckgDimensions[0] / 2, 
                        node.y - bckgDimensions[1] / 2, 
                        ...bckgDimensions, 
                        2 / globalScale
                    );
                    ctx.fill();
                    ctx.stroke();
                    
                    // Reset shadow for text
                    ctx.shadowBlur = 0;

                    // Draw Text
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillStyle = '#c9d1d9';
                    ctx.fillText(label, node.x, node.y);

                    node.__bckgDimensions = bckgDimensions; // for interaction
                }})
                .nodePointerAreaPaint((node, color, ctx) => {{
                    ctx.fillStyle = color;
                    const bckgDimensions = node.__bckgDimensions;
                    bckgDimensions && ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);
                }})
                .onNodeClick(node => {{
                    window.selectedNode = node;
                    showDetails(node);
                    
                    // Center/Zoom on click
                    Graph.centerAt(node.x, node.y, 1000);
                    Graph.zoom(6, 2000);
                }})
                .onBackgroundClick(() => {{
                    window.selectedNode = null;
                    closePanel();
                }});

            // --- Panel Logic ---
            function showDetails(node) {{
                const panel = document.getElementById('details-panel');
                const title = document.getElementById('panel-title');
                const content = document.getElementById('panel-content');
                
                title.innerText = node.group;
                title.style.color = colors[node.group] || colors['default'];
                
                let html = `<div style="margin-bottom:20px; font-size:1.2rem; font-weight:bold;">${{node.name}}</div>`;
                
                // Properties Table
                html += `<div class="section-header">Properties</div>`;
                html += `<table class="prop-table">`;
                for (const [key, val] of Object.entries(node.properties)) {{
                    if (key === 'screenshot' || key === 'screenshot_url') continue; // Skip internal fields
                    html += `<tr><td class="prop-key">${{key}}</td><td class="prop-val">${{val}}</td></tr>`;
                }}
                html += `</table>`;

                // Gallery / Screenshot
                if (node.properties.screenshot_url) {{
                    html += `<div class="section-header">Evidence</div>`;
                    html += `<div class="gallery-container">`;
                    html += `<img src="${{node.properties.screenshot_url}}" class="gallery-img" alt="Evidence">`;
                    html += `</div>`;
                }}

                content.innerHTML = html;
                panel.classList.add('open');
            }}

            function closePanel() {{
                document.getElementById('details-panel').classList.remove('open');
                window.selectedNode = null;
            }}
        </script>
    </body>
    </html>
    """
    
    components.html(html_code, height=800, scrolling=False)

    # Stats
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Nodes", len(data["nodes"]))
    with c2:
        st.metric("Relationships", len(data["links"]))
    with c3:
        st.metric("Groups", len(set(n["group"] for n in data["nodes"])))
