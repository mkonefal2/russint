import http.server
import socketserver
import json
import os
from neo4j import GraphDatabase
from dotenv import load_dotenv
from pathlib import Path
import mimetypes

# Load env vars from project root
project_root = Path(__file__).parent.parent.parent.parent
load_dotenv(project_root / ".env")

PORT = 8082
WEB_DIR = Path(__file__).parent

import urllib.parse

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/api/graph':
            self.handle_api_graph()
        elif self.path.startswith('/data/'):
            self.handle_data_file()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/update_node':
            self.handle_update_node()
        else:
            self.send_error(404, "Not Found")

    def handle_update_node(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            node_id = data.get('id')
            properties = data.get('properties')
            
            if not node_id or not properties:
                self.send_error(400, "Missing id or properties")
                return

            update_node_properties(node_id, properties)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
        except Exception as e:
            print(f"Error updating node: {e}")
            self.send_error(500, str(e))

    def handle_api_graph(self):
        try:
            data = get_graph_data()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(data).encode('utf-8'))
        except Exception as e:
            self.send_error(500, str(e))

    def handle_data_file(self):
        # Decode URL (e.g. %20 -> space)
        decoded_path = urllib.parse.unquote(self.path)
        
        # Map /data/... to project_root/data/...
        rel_path = decoded_path.lstrip('/') # data/evidence/...
        file_path = project_root / rel_path
        
        print(f"Requesting file: {file_path}")
        
        if file_path.exists() and file_path.is_file():
            self.send_response(200)
            mime_type, _ = mimetypes.guess_type(file_path)
            self.send_header('Content-type', mime_type or 'application/octet-stream')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            print(f"File not found: {file_path}")
            self.send_error(404, "File not found")

def get_driver():
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    if not uri or not user or not password:
        return None
    return GraphDatabase.driver(uri, auth=(user, password))

def get_graph_data(limit=500):
    driver = get_driver()
    if not driver:
        return {"nodes": [], "links": []}
    
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
            
            def process_node(node):
                nid = node.element_id if hasattr(node, 'element_id') else str(node.id)
                if 'id' in node: nid = node['id']
                props = dict(node)
                
                # Normalize screenshot path for web
                if 'screenshot' in props:
                    # Ensure it starts with data/ if it's relative
                    # If it's like "evidence/..." we might need to prepend "data/"
                    # But usually in this project it seems to be relative to project root or data root?
                    # Instructions said: "screenshot - ścieżka względna do pliku screenshotu (np. data/evidence/facebook/...)"
                    # So it should be fine.
                    pass

                return nid, {
                    "id": nid,
                    "name": node.get("name", node.get("title", "Unknown")),
                    "group": list(node.labels)[0] if node.labels else "Unknown",
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
            
    driver.close()
    return {"nodes": list(nodes.values()), "links": links}

def update_node_properties(node_id, properties):
    driver = get_driver()
    if not driver:
        raise Exception("Database connection failed")
        
    query = """
    MATCH (n {id: $id})
    SET n += $props
    RETURN n
    """
    
    with driver.session() as session:
        session.run(query, id=node_id, props=properties)

if __name__ == "__main__":
    try:
        os.chdir(WEB_DIR)
        print(f"Starting server at http://localhost:{PORT}")
        # Allow reuse address to avoid "Address already in use" errors
        socketserver.TCPServer.allow_reuse_address = True
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass
    except Exception as e:
        import traceback
        traceback.print_exc()
