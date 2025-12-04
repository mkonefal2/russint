import os
import json
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st

# Use neo4j driver if available; otherwise attempt to call local /api/graph
try:
    from neo4j import GraphDatabase
    _has_neo4j = True
except Exception:
    _has_neo4j = False

# Load env from project root
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / '.env')

NEO4J_URI = os.getenv('NEO4J_URI')
NEO4J_USER = os.getenv('NEO4J_USER')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD')
LOCAL_API = os.getenv('LOCAL_GRAPH_API', 'http://localhost:8082/api/graph')

st.set_page_config(page_title='RUSSINT Graph (Streamlit)', layout='wide')
st.title('RUSSINT — Interactive Graph (Streamlit)')

use_api = st.sidebar.checkbox('Fetch data from local HTTP API', value=True)
limit = st.sidebar.slider('Max links to load', 100, 2000, 500, step=100)
refresh = st.sidebar.button('Refresh')

@st.cache(ttl=30, suppress_st_warning=True)
def get_graph_from_neo4j(limit=500):
    if not _has_neo4j:
        st.error('neo4j driver not installed in this environment')
        return {'nodes': [], 'links': []}
    if not (NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD):
        st.error('NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD not set in .env')
        return {'nodes': [], 'links': []}

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    query = '''
    MATCH (n)-[r]->(m)
    RETURN n, r, m
    LIMIT $limit
    '''

    nodes = {}
    links = []
    with driver.session() as session:
        result = session.run(query, limit=limit)
        for record in result:
            n = record['n']
            m = record['m']
            r = record['r']

            def process_node(node):
                nid = str(node.id)
                if 'id' in node:
                    nid = node['id']
                props = dict(node)
                return nid, {
                    'id': nid,
                    'name': node.get('name', node.get('title', 'Unknown')),
                    'group': list(node.labels)[0] if node.labels else 'Unknown',
                    'properties': props
                }

            src_id, src_node = process_node(n)
            tgt_id, tgt_node = process_node(m)

            if src_id not in nodes:
                nodes[src_id] = src_node
            if tgt_id not in nodes:
                nodes[tgt_id] = tgt_node

            links.append({'source': src_id, 'target': tgt_id, 'type': r.type, 'properties': dict(r)})

    driver.close()
    return {'nodes': list(nodes.values()), 'links': links}

@st.cache(ttl=10)
def get_graph_from_api(api_url, limit=500):
    import requests
    try:
        r = requests.get(api_url, params={'limit': limit}, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f'Failed to fetch from API: {e}')
        return {'nodes': [], 'links': []}

# Choose data source
if use_api:
    data = get_graph_from_api(LOCAL_API, limit=limit)
else:
    data = get_graph_from_neo4j(limit=limit)

if not data or (not data.get('nodes') and not data.get('links')):
    st.warning('No graph data loaded. Check Neo4j connection or API.')

# Build HTML/JS for visualization (minimal bootstrap of force-graph)
# Use unpkg CDN for force-graph
json_data = json.dumps(data).replace('</', '<\/')

html = '''
<!doctype html>
<html>
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<style>
  html, body {{ margin:0; padding:0; height:100%; background:#0d1117; color:#c9d1d9; }}
  #graph {{ width:100%; height:100%; }}
</style>
</head>
<body>
<div id="graph"></div>
<script src="https://unpkg.com/three@0.148.0/build/three.min.js"></script>
<script src="https://unpkg.com/force-graph/dist/force-graph.min.js"></script>
<script>
(function(){
    const data = __GRAPH_JSON__;
  const Graph = ForceGraph()(document.getElementById('graph'))
    .graphData(data)
    .backgroundColor('#0d1117')
    .nodeId('id')
    .nodeLabel('name')
    .linkDirectionalParticles(0)
    .nodeRelSize(6)
    .linkWidth(1.5)
    .linkColor('rgba(88,166,255,0.4)')
    .nodeCanvasObject((node, ctx, globalScale) => {{
        const label = node.name || node.id;
        const fontSize = 10 / Math.sqrt(globalScale);
        ctx.font = `${{fontSize}}px Sans-Serif`;
        const textWidth = ctx.measureText(label).width;
        const bckgDimensions = [textWidth + fontSize, fontSize * 1.4];
        ctx.fillStyle = 'rgba(22,27,34,0.9)';
        ctx.fillRect(node.x - bckgDimensions[0]/2, node.y - bckgDimensions[1]/2, ...bckgDimensions);
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = '#c9d1d9';
        ctx.fillText(label, node.x, node.y);
    }})
    .onNodeClick(node => {{
        const payload = JSON.stringify(node, null, 2);
        console.log('clicked', node);
    }});
  // Fit view
  setTimeout(() => Graph.zoomToFit(400), 500);
})();
</script>
</body>
</html>
'''

# Inject JSON safely (replace placeholder)
html = html.replace('__GRAPH_JSON__', json_data)

# Render via streamlit component
st.components.v1.html(html, height=800, scrolling=True)

st.markdown('---')
st.write('Nodes:', len(data.get('nodes', [])), ' Links:', len(data.get('links', [])))

st.caption('Force-graph rendered inside Streamlit using embedded HTML/JS. Click nodes to see console logs in the browser devtools.')
