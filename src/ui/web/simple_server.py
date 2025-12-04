import http.server
import socketserver
import os

PORT = 8083
WEB_DIR = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    pass

if __name__ == "__main__":
    os.chdir(WEB_DIR)
    print(f"Starting simple server at http://localhost:{PORT}")
    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
