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
        elif self.path == '/api/create_node':
            self.handle_create_node()
        elif self.path == '/api/create_edge':
            self.handle_create_edge()
        elif self.path == '/api/delete_node':
            self.handle_delete_node()
        elif self.path == '/api/delete_edge':
            self.handle_delete_edge()
        elif self.path == '/api/find_node':
            self.handle_find_node()
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

    def handle_create_node(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            create_node_in_db(data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
        except Exception as e:
            print(f"Error creating node: {e}")
            self.send_error(500, str(e))

    def handle_create_edge(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            create_edge_in_db(data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
        except Exception as e:
            print(f"Error creating edge: {e}")
            self.send_error(500, str(e))

    def handle_delete_node(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            delete_node_in_db(data.get('id'))
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
        except Exception as e:
            print(f"Error deleting node: {e}")
            self.send_error(500, str(e))

    def handle_delete_edge(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            delete_edge_in_db(data)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
        except Exception as e:
            print(f"Error deleting edge: {e}")
            self.send_error(500, str(e))

    def handle_find_node(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            node_id = data.get('id')
            if not node_id:
                self.send_error(400, 'Missing id')
                return

            node = find_node_in_db(node_id)

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({ 'node': node }).encode('utf-8'))
        except Exception as e:
            print(f"Error finding node: {e}")
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

def get_graph_data(limit=10000):
    driver = get_driver()
    if not driver:
        return {"nodes": [], "links": []}

    nodes = {}
    links = []

    def process_node(node):
        nid = node.element_id if hasattr(node, 'element_id') else str(node.id)
        # prefer explicit 'id' property if present
        try:
            if 'id' in node:
                nid = node['id']
        except Exception:
            pass
        props = dict(node)
        return nid, {
            "id": nid,
            "name": node.get("name", node.get("title", "Unknown")),
            "group": list(node.labels)[0] if node.labels else "Unknown",
            "properties": props
        }

    with driver.session() as session:
        # 1) Fetch standalone nodes (limit applied)
        node_query = """
        MATCH (n)
        RETURN n
        LIMIT $limit
        """
        try:
            results = session.run(node_query, limit=limit)
            for rec in results:
                n = rec['n']
                nid, nobj = process_node(n)
                if nid not in nodes:
                    nodes[nid] = nobj
        except Exception as e:
            # fallback: ignore node-only query failures
            print(f"Warning fetching nodes: {e}")

        # 2) Fetch relationships and ensure connected nodes are present
        rel_query = """
        MATCH (s)-[r]->(t)
        RETURN s, r, t
        LIMIT $limit
        """
        result = session.run(rel_query, limit=limit)
        for record in result:
            s = record['s']
            t = record['t']
            r = record['r']

            src_id, src_node = process_node(s)
            tgt_id, tgt_node = process_node(t)

            if src_id not in nodes:
                nodes[src_id] = src_node
            if tgt_id not in nodes:
                nodes[tgt_id] = tgt_node

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

def create_node_in_db(data):
    driver = get_driver()
    if not driver:
        raise Exception("Database connection failed")
    
    # data: {id, group, properties}
    # group is the Label
    label = data.get('group', 'Entity')
    # Sanitize label to avoid injection (basic check)
    if not label.isalnum():
        label = "Entity"
        
    props = data.get('properties', {})
    node_id = data.get('id')
    if node_id:
        props['id'] = node_id
    
    # Dynamic label in Cypher requires APOC or string formatting (risky if not sanitized)
    # Using string formatting with sanitized label
    query = f"""
    MERGE (n:{label} {{id: $id}})
    SET n += $props
    RETURN n
    """
    
    with driver.session() as session:
        session.run(query, id=node_id, props=props)

def create_edge_in_db(data):
    driver = get_driver()
    if not driver:
        raise Exception("Database connection failed")
        
    source_id = data.get('source')
    target_id = data.get('target')
    rel_type = data.get('type', 'RELATED_TO')
    props = data.get('properties', {})
    
    # Sanitize rel_type
    if not rel_type.replace('_', '').isalnum():
        rel_type = "RELATED_TO"
        
    query = f"""
    MATCH (s {{id: $source_id}})
    MATCH (t {{id: $target_id}})
    MERGE (s)-[r:{rel_type}]->(t)
    SET r += $props
    RETURN r
    """
    
    with driver.session() as session:
        session.run(query, source_id=source_id, target_id=target_id, props=props)

def delete_node_in_db(node_id):
    driver = get_driver()
    if not driver:
        raise Exception("Database connection failed")
        
    query = """
    MATCH (n {id: $id})
    DETACH DELETE n
    """
    
    with driver.session() as session:
        session.run(query, id=node_id)

def delete_edge_in_db(data):
    driver = get_driver()
    if not driver:
        raise Exception("Database connection failed")
        
    source_id = data.get('source')
    target_id = data.get('target')
    rel_type = data.get('type')
    
    # Sanitize rel_type
    if not rel_type.replace('_', '').isalnum():
        # If invalid type, maybe try to delete any relationship?
        # For safety, let's require a valid type or fail.
        raise Exception("Invalid relationship type")

    query = f"""
    MATCH (s {{id: $source_id}})-[r:{rel_type}]->(t {{id: $target_id}})
    DELETE r
    """
    
    with driver.session() as session:
        session.run(query, source_id=source_id, target_id=target_id)

def find_node_in_db(node_id):
    driver = get_driver()
    if not driver:
        raise Exception("Database connection failed")

    query = """
    MATCH (n {id: $id})
    RETURN n
    LIMIT 1
    """
    with driver.session() as session:
        result = session.run(query, id=node_id)
        for record in result:
            node = record['n']
            props = dict(node)
            nid = props.get('id', node.element_id if hasattr(node, 'element_id') else str(node.id))
            return {
                'id': nid,
                'name': node.get('name', nid),
                'group': list(node.labels)[0] if node.labels else 'Unknown',
                'properties': props
            }
    return None

# ThreadingTCPServer for handling multiple concurrent requests
class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == "__main__":
    try:
        os.chdir(WEB_DIR)
        print(f"Starting server at http://localhost:{PORT}")
        with ThreadedTCPServer(("", PORT), Handler) as httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                pass
    except Exception as e:
        import traceback
        traceback.print_exc()
