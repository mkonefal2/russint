"""
Social Media Manager - Backend API Server
Serwer HTTP obsługujący API dla aplikacji Social Media Manager.
Obsługuje: Instagram (ig-*) oraz Facebook (fb-*)
"""
import http.server
import socketserver
import json
import os
import shutil
import uuid
import sys
from pathlib import Path
from datetime import datetime
import urllib.parse
import cgi
import subprocess
import threading

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent.parent
SCRAPER_SCRIPT = PROJECT_ROOT / "src" / "collectors" / "instagram_scraper.py"
BACKUP_DIR = PROJECT_ROOT / "data" / "backup"
WEB_DIR = Path(__file__).resolve().parent

# Add src to path for imports
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Import DuckDB manager and Neo4j client
from db.posts_db import get_posts_db
from graph.neo4j_client import get_client as get_neo4j_client

# Graph data paths
GRAPH_NODES_FILE = PROJECT_ROOT / "data" / "raw" / "graph_nodes.json"
GRAPH_EDGES_FILE = PROJECT_ROOT / "data" / "raw" / "graph_edges.json"

# Entity types configuration
ENTITY_TYPES = {
    'person': {'icon': 'fas fa-user', 'color': '#e87fb0', 'label': 'Osoba'},
    'organization': {'icon': 'fas fa-building', 'color': '#5ba4e6', 'label': 'Organizacja'},
    'profile': {'icon': 'fas fa-id-card', 'color': '#6dd490', 'label': 'Profil'},
    'event': {'icon': 'fas fa-calendar', 'color': '#e8a860', 'label': 'Wydarzenie'},
    'post': {'icon': 'fas fa-file-alt', 'color': '#c9a0e8', 'label': 'Post'},
    'page': {'icon': 'fas fa-globe', 'color': '#60c0e8', 'label': 'Strona WWW'},
    'group': {'icon': 'fas fa-users', 'color': '#e86060', 'label': 'Grupa'},
    'channel': {'icon': 'fab fa-youtube', 'color': '#ff0000', 'label': 'Kanał'},
    'symbol': {'icon': 'fas fa-flag', 'color': '#ffd700', 'label': 'Symbol'}
}

# Relationship types
RELATIONSHIP_TYPES = [
    'HAS_PROFILE', 'PUBLISHED', 'ANNOUNCES', 'ORGANIZES', 'SPEAKER_AT',
    'MENTIONS', 'PROMOTES', 'ATTACKS', 'REPOSTS', 'SHARES_CONTENT_FROM',
    'MEMBER_OF', 'COLLABORATES_WITH', 'LINKS_TO', 'FEATURED_ON',
    'WORKS_AT', 'AFFILIATED_WITH', 'FOUNDED', 'LEADS', 'PARTICIPATES_IN'
]

# Platform configs
PLATFORMS = {
    'instagram': {
        'prefix': 'ig',
        'data_dir': PROJECT_ROOT / "data" / "raw" / "instagram",
        'evidence_dir': PROJECT_ROOT / "data" / "evidence" / "instagram",
        'posts_subdir': 'posts',
        'icon': 'fab fa-instagram',
        'color': '#E1306C'
    },
    'facebook': {
        'prefix': 'fb',
        'data_dir': PROJECT_ROOT / "data" / "raw" / "facebook",
        'evidence_dir': PROJECT_ROOT / "data" / "evidence" / "facebook",
        'posts_subdir': '',  # FB trzyma screenshoty bezpośrednio w katalogu profilu
        'icon': 'fab fa-facebook',
        'color': '#1877F2'
    }
}

PORT = 8084


class SocialMediaAPIHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler for Social Media Manager API."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEB_DIR), **kwargs)
    
    def parse_profile_id(self, prefixed_profile):
        """Parse prefixed profile ID (ig-handle or fb-handle) into platform and handle."""
        if prefixed_profile.startswith('ig-'):
            return 'instagram', prefixed_profile[3:]
        elif prefixed_profile.startswith('fb-'):
            return 'facebook', prefixed_profile[3:]
        else:
            # Domyślnie Instagram dla kompatybilności wstecznej
            return 'instagram', prefixed_profile
    
    def get_platform_config(self, platform):
        """Get config for platform."""
        return PLATFORMS.get(platform, PLATFORMS['instagram'])
    
    def send_json(self, data, status=200):
        """Send JSON response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def send_error_json(self, message, status=400):
        """Send JSON error response."""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'error': message}, ensure_ascii=False).encode('utf-8'))
    
    def do_OPTIONS(self):
        """Handle CORS preflight."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """Handle GET requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        # Normalize paths that should serve the main single-page app
        if path in ('/', '', '/index.html', '/instagram', '/instagram/', '/instagram/index.html', '/social', '/social/'):
            index_file = WEB_DIR / 'index.html'
            if index_file.exists():
                with open(index_file, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Content-Length', str(len(content)))
                self.end_headers()
                self.wfile.write(content)
                return
            else:
                self.send_error(404, 'File not found')
                return
        
        # API Routes - unified endpoint /api/social/*
        if path == '/api/social/profiles':
            self.handle_get_profiles()
        elif path.startswith('/api/social/posts/'):
            prefixed_profile = urllib.parse.unquote(path.split('/')[-1])
            self.handle_get_posts(prefixed_profile)
        elif path.startswith('/api/social/post/'):
            parts = path.split('/')
            if len(parts) >= 5:
                prefixed_profile = urllib.parse.unquote(parts[4])
                post_id = urllib.parse.unquote(parts[5]) if len(parts) > 5 else None
                self.handle_get_post(prefixed_profile, post_id)
            else:
                self.send_error_json('Invalid path', 400)
        # Legacy Instagram API support
        elif path == '/api/instagram/profiles':
            self.handle_get_profiles()
        elif path.startswith('/api/instagram/posts/'):
            profile = urllib.parse.unquote(path.split('/')[-1])
            self.handle_get_posts(f"ig-{profile}")
        elif path.startswith('/api/instagram/post/'):
            parts = path.split('/')
            if len(parts) >= 5:
                profile, post_id = urllib.parse.unquote(parts[4]), urllib.parse.unquote(parts[5])
                self.handle_get_post(f"ig-{profile}", post_id)
            else:
                self.send_error_json('Invalid path', 400)
        elif path.startswith('/data/'):
            # Serve static data files (evidence)
            self.handle_data_file()
        # ==========================================
        # GRAPH API - GET
        # ==========================================
        elif path == '/api/graph/nodes':
            self.handle_get_graph_nodes()
        elif path == '/api/graph/edges':
            self.handle_get_graph_edges()
        elif path == '/api/graph/entity-types':
            self.handle_get_entity_types()
        elif path == '/api/graph/relationship-types':
            self.handle_get_relationship_types()
        elif path.startswith('/api/graph/node/'):
            node_id = urllib.parse.unquote(path.split('/')[-1])
            self.handle_get_graph_node(node_id)
        elif path.startswith('/api/graph/node-edges/'):
            node_id = urllib.parse.unquote(path.split('/')[-1])
            self.handle_get_node_edges(node_id)
        elif path.startswith('/api/graph/search'):
            query_params = urllib.parse.parse_qs(parsed.query)
            search_query = query_params.get('q', [''])[0]
            self.handle_search_graph(search_query)
        else:
            # Serve static files from web directory
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        # New unified API
        if path.startswith('/api/social/upload/'):
            parts = path.split('/')
            if len(parts) >= 6:
                prefixed_profile, post_id = parts[4], parts[5]
                self.handle_upload(prefixed_profile, post_id)
            else:
                self.send_error_json('Invalid path', 400)
        elif path == '/api/social/post':
            # Create new post
            self.handle_create_post()
        elif path == '/api/social/scrape':
            # Start scraper
            self.handle_start_scrape()
        elif path == '/api/social/profile':
            # Create new profile
            self.handle_create_profile()
        # ==========================================
        # GRAPH API - POST
        # ==========================================
        elif path == '/api/graph/node':
            self.handle_create_graph_node()
        elif path == '/api/graph/edge':
            self.handle_create_graph_edge()
        elif path == '/api/graph/sync':
            self.handle_sync_to_neo4j()
        # Legacy Instagram API
        elif path.startswith('/api/instagram/upload/'):
            parts = path.split('/')
            if len(parts) >= 6:
                profile, post_id = parts[4], parts[5]
                self.handle_upload(f"ig-{profile}", post_id)
            else:
                self.send_error_json('Invalid path', 400)
        else:
            self.send_error_json('Not Found', 404)
    
    def do_PUT(self):
        """Handle PUT requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        # New unified API
        if path.startswith('/api/social/post/'):
            parts = path.split('/')
            if len(parts) >= 5:
                prefixed_profile, post_id = parts[4], parts[5]
                self.handle_update_post(prefixed_profile, post_id)
            else:
                self.send_error_json('Invalid path', 400)
        # ==========================================
        # GRAPH API - PUT
        # ==========================================
        elif path.startswith('/api/graph/node/'):
            node_id = urllib.parse.unquote(path.split('/')[-1])
            self.handle_update_graph_node(node_id)
        elif path.startswith('/api/graph/edge/'):
            edge_id = urllib.parse.unquote(path.split('/')[-1])
            self.handle_update_graph_edge(edge_id)
        # Legacy Instagram API
        elif path.startswith('/api/instagram/post/'):
            parts = path.split('/')
            if len(parts) >= 5:
                profile, post_id = parts[4], parts[5]
                self.handle_update_post(f"ig-{profile}", post_id)
            else:
                self.send_error_json('Invalid path', 400)
        else:
            self.send_error_json('Not Found', 404)
    
    def do_DELETE(self):
        """Handle DELETE requests."""
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        # New unified API
        if path.startswith('/api/social/screenshot/'):
            parts = path.split('/')
            if len(parts) >= 6:
                prefixed_profile, post_id = parts[4], parts[5]
                self.handle_delete_screenshot(prefixed_profile, post_id)
            else:
                self.send_error_json('Invalid path', 400)
        elif path.startswith('/api/social/post/'):
            parts = path.split('/')
            if len(parts) >= 5:
                prefixed_profile, post_id = parts[4], parts[5]
                self.handle_delete_post(prefixed_profile, post_id)
            else:
                self.send_error_json('Invalid path', 400)
        # Legacy Instagram API
        elif path.startswith('/api/instagram/screenshot/'):
            parts = path.split('/')
            if len(parts) >= 6:
                profile, post_id = parts[4], parts[5]
                self.handle_delete_screenshot(f"ig-{profile}", post_id)
            else:
                self.send_error_json('Invalid path', 400)
        elif path.startswith('/api/instagram/post/'):
            parts = path.split('/')
            if len(parts) >= 5:
                profile, post_id = parts[4], parts[5]
                self.handle_delete_post(f"ig-{profile}", post_id)
            else:
                self.send_error_json('Invalid path', 400)
        # ==========================================
        # GRAPH API - DELETE
        # ==========================================
        elif path.startswith('/api/graph/node/'):
            node_id = urllib.parse.unquote(path.split('/')[-1])
            self.handle_delete_graph_node(node_id)
        elif path.startswith('/api/graph/edge/'):
            edge_id = urllib.parse.unquote(path.split('/')[-1])
            self.handle_delete_graph_edge(edge_id)
        else:
            self.send_error_json('Not Found', 404)
    
    # ==========================================
    # API HANDLERS
    # ==========================================
    
    def handle_get_profiles(self):
        """Get list of available profiles from DuckDB."""
        try:
            db = get_posts_db()
            profiles = []
            
            for platform_name, config in PLATFORMS.items():
                prefix = config['prefix']
                
                # Get unique handles from DuckDB for this platform
                handles = db.get_handles(platform=platform_name)
                
                for handle in handles:
                    # Get post count for this profile
                    post_count = db.count_posts(platform=platform_name, handle=handle)
                    
                    profiles.append({
                        'id': f"{prefix}-{handle}",
                        'name': handle,
                        'platform': platform_name,
                        'prefix': prefix,
                        'icon': config['icon'],
                        'color': config['color'],
                        'postCount': post_count
                    })
            
            # Sort: Instagram first, then Facebook, then by name
            profiles.sort(key=lambda x: (x['platform'] != 'instagram', x['name'].lower()))
            
            self.send_json(profiles)
        except Exception as e:
            self.send_error_json(str(e), 500)
    
    def handle_get_posts(self, prefixed_profile):
        """Get list of posts for a profile from DuckDB."""
        try:
            platform, profile = self.parse_profile_id(prefixed_profile)
            config = self.get_platform_config(platform)
            evidence_dir = config['evidence_dir']
            posts_subdir = config['posts_subdir']
            
            # Get posts from DuckDB
            db = get_posts_db()
            db_posts = db.get_posts(platform=platform, handle=profile, limit=1000)
            
            posts = []
            # Dla FB posts_subdir jest pusty, więc używamy bezpośrednio katalogu profilu
            if posts_subdir:
                evidence_posts_dir = evidence_dir / profile / posts_subdir
            else:
                evidence_posts_dir = evidence_dir / profile
            evidence_images_dir = evidence_dir / profile / "images"
            
            for db_post in db_posts:
                post_id = db_post['id']
                
                # Find thumbnail - scan evidence folder for first matching screenshot
                thumbnail = None
                if evidence_posts_dir.exists():
                    # Look for files starting with post_id
                    for img_file in sorted(evidence_posts_dir.glob(f"{post_id}*")):
                        if img_file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']:
                            thumbnail = img_file.name
                            break
                
                # Fallback to screenshot_path from DB
                if not thumbnail and db_post.get('screenshot_path'):
                    screenshot_field = db_post['screenshot_path']
                    thumb_name = Path(screenshot_field).name
                    if evidence_posts_dir.exists():
                        thumb_path = evidence_posts_dir / thumb_name
                        if thumb_path.exists():
                            thumbnail = thumb_name
                
                # Count screenshots - based on actual files in evidence folder
                screenshot_count = 0
                if evidence_posts_dir.exists():
                    screenshot_count = len(list(evidence_posts_dir.glob(f"{post_id}*")))
                
                # Fallback to 1 if screenshot_path exists
                if screenshot_count == 0 and db_post.get('screenshot_path'):
                    screenshot_count = 1
                
                # Get metadata for carousel images (only for Instagram)
                metadata_dict = db_post.get('metadata')
                if isinstance(metadata_dict, str):
                    try:
                        metadata_dict = json.loads(metadata_dict)
                    except:
                        metadata_dict = {}
                
                image_count = len(metadata_dict.get('images', [])) if metadata_dict else 0
                
                # Determine content type (post/story)
                content_type = 'post'
                url = db_post.get('post_url') or ''
                if url and ('/stories/' in url or '/story/' in url):
                    content_type = 'story'
                
                post_date = db_post.get('date_posted')
                if post_date:
                    post_date = str(post_date)
                
                created_at = db_post.get('created_at')
                if created_at:
                    created_at = str(created_at)
                
                posts.append({
                    'id': post_id,
                    'thumbnail': thumbnail,
                    'date': post_date or created_at or '',
                    'scraped_at': created_at or '',
                    'text': (db_post.get('text') or db_post.get('raw_text_preview') or '')[:100],
                    'screenshotCount': screenshot_count,
                    'imageCount': image_count,
                    'contentType': content_type,
                    'platform': platform
                })
            
            self.send_json(posts)
        except Exception as e:
            self.send_error_json(str(e), 500)
    
    def handle_get_post(self, prefixed_profile, post_id):
        """Get detailed post data."""
        try:
            platform, profile = self.parse_profile_id(prefixed_profile)
            config = self.get_platform_config(platform)
            data_dir = config['data_dir']
            evidence_dir = config['evidence_dir']
            posts_subdir = config['posts_subdir']
            
            json_path = data_dir / profile / f"{post_id}.json"
            if not json_path.exists():
                self.send_error_json('Post not found', 404)
                return
            
            with open(json_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            evidence_profile_dir = evidence_dir / profile
            if posts_subdir:
                posts_dir = evidence_profile_dir / posts_subdir
            else:
                posts_dir = evidence_profile_dir
            images_dir = evidence_profile_dir / "images"
            
            # Collect screenshots
            screenshots = []
            
            # From metadata list
            if 'screenshots' in metadata and isinstance(metadata['screenshots'], list):
                for s in metadata['screenshots']:
                    s_name = Path(s).name
                    if (posts_dir / s_name).exists():
                        screenshots.append(s_name)
            
            # From metadata single
            if 'screenshot' in metadata and metadata['screenshot']:
                s = metadata['screenshot']
                s_name = Path(s).name
                if (posts_dir / s_name).exists() and s_name not in screenshots:
                    screenshots.append(s_name)
            
            # Scan directory fallback
            if posts_dir.exists():
                for f in posts_dir.iterdir():
                    if f.is_file() and post_id in f.stem and f.name not in screenshots:
                        screenshots.append(f.name)
            
            # Collect carousel images (only for Instagram)
            images = []
            if 'images' in metadata and isinstance(metadata['images'], list):
                for img_id in metadata['images']:
                    for ext in ['.jpg', '.jpeg', '.png', '.heic', '.webp']:
                        img_name = f"{img_id}{ext}"
                        if (images_dir / img_name).exists():
                            images.append(img_name)
                            break

            # Sanitize metadata screenshot links -> prefer local filenames when available
            try:
                sanitized_meta = dict(metadata)
                # normalize single screenshot
                if 'screenshot' in sanitized_meta and sanitized_meta['screenshot']:
                    s = str(sanitized_meta['screenshot'])
                    s_name = Path(s).name
                    if (posts_dir / s_name).exists():
                        sanitized_meta['screenshot'] = s_name
                    else:
                        # remove full remote URL if local not present to avoid external hotlinking
                        sanitized_meta['screenshot'] = ''

                # normalize screenshots list
                if 'screenshots' in sanitized_meta and isinstance(sanitized_meta['screenshots'], list):
                    new_list = []
                    for s in sanitized_meta['screenshots']:
                        s_name = Path(s).name
                        if (posts_dir / s_name).exists():
                            new_list.append(s_name)
                    sanitized_meta['screenshots'] = new_list
            except Exception:
                sanitized_meta = metadata

            self.send_json({
                'id': post_id,
                'platform': platform,
                'metadata': sanitized_meta,
                'screenshots': screenshots,
                'images': images
            })
        except Exception as e:
            self.send_error_json(str(e), 500)
    
    def handle_update_post(self, prefixed_profile, post_id):
        """Update post metadata."""
        try:
            platform, profile = self.parse_profile_id(prefixed_profile)
            config = self.get_platform_config(platform)
            data_dir = config['data_dir']
            
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            metadata = data.get('metadata')
            if not metadata:
                self.send_error_json('Missing metadata', 400)
                return
            
            json_path = data_dir / profile / f"{post_id}.json"
            if not json_path.exists():
                self.send_error_json('Post not found', 404)
                return
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            self.send_json({'status': 'success'})
        except Exception as e:
            self.send_error_json(str(e), 500)
    
    def handle_create_post(self):
        """Create a new post entry."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            prefixed_profile = data.get('profile')
            if not prefixed_profile:
                self.send_error_json('Missing profile', 400)
                return
            
            platform, profile = self.parse_profile_id(prefixed_profile)
            config = self.get_platform_config(platform)
            data_dir = config['data_dir']
            evidence_dir = config['evidence_dir']
            posts_subdir = config['posts_subdir']
            
            # Utwórz katalogi jeśli nie istnieją
            profile_data_dir = data_dir / profile
            profile_data_dir.mkdir(parents=True, exist_ok=True)
            
            profile_evidence_dir = evidence_dir / profile / posts_subdir
            profile_evidence_dir.mkdir(parents=True, exist_ok=True)
            
            # Generuj ID dla nowego posta
            timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%S')
            short_id = str(uuid.uuid4())[:8]
            post_id = f"{config['prefix']}_{profile}_{timestamp}_{short_id}"
            
            # Utwórz metadata
            metadata = {
                'id': post_id,
                'handle': profile,
                'url': data.get('url', ''),
                'post_url': data.get('url', ''),
                'text': data.get('caption', ''),
                'caption': data.get('caption', ''),
                'date_posted': data.get('date', ''),
                'scraped_at': datetime.utcnow().isoformat(),
                'screenshot': '',
                'screenshots': [],
                'manually_created': True
            }
            
            # Zapisz JSON
            json_path = profile_data_dir / f"{post_id}.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            self.send_json({
                'status': 'success',
                'post_id': post_id,
                'profile': prefixed_profile
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_error_json(str(e), 500)
    
    def handle_create_profile(self):
        """Create a new profile (empty folder structure)."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            platform = data.get('platform', 'instagram')
            handle = data.get('handle', '').strip()
            
            if not handle:
                self.send_error_json('Missing handle', 400)
                return
            
            # Sanitize handle (only alphanumeric, underscore, dots)
            import re
            if not re.match(r'^[\w.]+$', handle):
                self.send_error_json('Invalid handle format', 400)
                return
            
            config = self.get_platform_config(platform)
            data_dir = config['data_dir']
            evidence_dir = config['evidence_dir']
            posts_subdir = config['posts_subdir']
            
            # Check if already exists
            profile_data_dir = data_dir / handle
            if profile_data_dir.exists():
                self.send_error_json(f'Profil {handle} już istnieje', 400)
                return
            
            # Create directories
            profile_data_dir.mkdir(parents=True, exist_ok=True)
            
            if posts_subdir:
                (evidence_dir / handle / posts_subdir).mkdir(parents=True, exist_ok=True)
            else:
                (evidence_dir / handle).mkdir(parents=True, exist_ok=True)
            (evidence_dir / handle / 'images').mkdir(parents=True, exist_ok=True)
            
            self.send_json({
                'status': 'success',
                'profile_id': f"{config['prefix']}-{handle}",
                'handle': handle,
                'platform': platform
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_error_json(str(e), 500)
    
    def handle_start_scrape(self):
        """Scrape single Instagram post by URL."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            post_url = data.get('url', '').strip()
            
            if not post_url:
                self.send_error_json('Missing post URL', 400)
                return
            
            # Parse Instagram URL to get handle and post_id
            # Formats: 
            # https://www.instagram.com/p/ABC123/
            # https://www.instagram.com/reel/ABC123/
            # https://instagram.com/p/ABC123/?utm_source=...
            import re
            
            # Extract post shortcode
            match = re.search(r'instagram\.com/(?:p|reel|reels)/([A-Za-z0-9_-]+)', post_url)
            if not match:
                self.send_error_json('Nieprawidłowy URL posta Instagram. Użyj formatu: instagram.com/p/XXX lub instagram.com/reel/XXX', 400)
                return
            
            post_id = match.group(1)
            
            # We'll need to extract handle from the page itself (or user provides it)
            handle = data.get('handle', '').strip()
            
            if not handle:
                # Try to auto-detect from profile URL if provided, otherwise ask
                self.send_error_json('Podaj nazwę profilu (@handle) - będzie automatycznie utworzony jeśli nowy', 400)
                return
            
            # Sanitize handle
            handle = re.sub(r'[^\w.]', '', handle)
            if not handle:
                self.send_error_json('Nieprawidłowa nazwa profilu', 400)
                return
            
            config = self.get_platform_config('instagram')
            data_dir = config['data_dir']
            evidence_dir = config['evidence_dir']
            
            # Auto-create profile directories if they don't exist
            profile_data_dir = data_dir / handle
            profile_posts_dir = evidence_dir / handle / 'posts'
            profile_images_dir = evidence_dir / handle / 'images'
            
            is_new_profile = not profile_data_dir.exists()
            
            profile_data_dir.mkdir(parents=True, exist_ok=True)
            profile_posts_dir.mkdir(parents=True, exist_ok=True)
            profile_images_dir.mkdir(parents=True, exist_ok=True)
            
            # Run scraper for single post in background
            def run_single_post_scraper():
                print(f"[Scraper] Scraping post {post_id} from @{handle}...")
                
                try:
                    from playwright.sync_api import sync_playwright
                    import time as _time
                    
                    user_data_dir = str(PROJECT_ROOT / 'chrome_data')
                    
                    with sync_playwright() as p:
                        ctx = p.chromium.launch_persistent_context(
                            user_data_dir, 
                            headless=False, 
                            channel='chrome',
                            args=['--start-maximized'],
                            viewport=None
                        )
                        page = ctx.pages[0] if ctx.pages else ctx.new_page()
                        
                        # Navigate to post
                        clean_url = post_url.split('?')[0]
                        print(f"[Scraper] Opening: {clean_url}")
                        page.goto(clean_url)
                        _time.sleep(2)
                        
                        # Check if login required
                        if 'login' in page.url.lower():
                            print("[Scraper] ⚠️  Login required - please log in manually in the browser")
                            print("[Scraper] Press ENTER in server console after logging in...")
                            input()
                            page.goto(clean_url)
                            _time.sleep(2)
                        
                        # =============================================
                        # DETECT NUMBER OF SLIDES
                        # =============================================
                        slide_count = 1
                        
                        # Method 1: Count indicator dots (most reliable)
                        try:
                            # Instagram uses small dots under carousel posts
                            dots = page.locator('article div._acnb, article div[class*="Indicator"]').all()
                            if dots:
                                slide_count = len(dots)
                                print(f"[Scraper] 📊 Detected {slide_count} slides via indicator dots")
                        except Exception:
                            pass
                        
                        # Method 2: Try API endpoint for sidecar data
                        if slide_count == 1:
                            try:
                                api_data = page.evaluate(f"""
                                    () => fetch('/p/{post_id}/?__a=1&__d=dis')
                                        .then(r => r.ok ? r.json() : null)
                                        .catch(() => null)
                                """)
                                if api_data:
                                    sm = api_data.get('graphql', {}).get('shortcode_media') or \
                                         (api_data.get('items') or [{}])[0]
                                    if sm and sm.get('edge_sidecar_to_children'):
                                        edges = sm.get('edge_sidecar_to_children', {}).get('edges', [])
                                        if edges:
                                            slide_count = len(edges)
                                            print(f"[Scraper] 📊 Detected {slide_count} slides via API")
                            except Exception:
                                pass
                        
                        # Method 3: Check for next button (indicates carousel)
                        if slide_count == 1:
                            try:
                                next_btn = page.locator('article button[aria-label*="Next"], article button[aria-label*="Dalej"], article div[class*="CornerCursorRight"]').first
                                if next_btn and next_btn.is_visible():
                                    # Has carousel, probe for count
                                    slide_count = 2  # At least 2
                                    print(f"[Scraper] 📊 Carousel detected (next button visible)")
                            except Exception:
                                pass
                        
                        # Method 4: Probe img_index until it fails (fallback)
                        if slide_count <= 2:
                            print(f"[Scraper] 🔍 Probing for slides...")
                            for i in range(1, 15):  # Max 15 slides
                                try:
                                    test_url = f"{clean_url}?img_index={i}"
                                    page.goto(test_url, wait_until='domcontentloaded', timeout=5000)
                                    _time.sleep(0.5)
                                    
                                    # Check if we're still on the post
                                    if 'login' in page.url.lower() or post_id not in page.url:
                                        break
                                    
                                    # Check if article exists
                                    art = page.locator('article').first
                                    if not art or not art.is_visible():
                                        break
                                    
                                    slide_count = i
                                except Exception:
                                    break
                            
                            print(f"[Scraper] 📊 Detected {slide_count} slides via probing")
                        
                        # =============================================
                        # SCRAPE ALL SLIDES
                        # =============================================
                        print(f"[Scraper] 📸 Starting to capture {slide_count} slide(s)...")
                        
                        screenshots_saved = []
                        
                        for slide_num in range(1, slide_count + 1):
                            try:
                                if slide_count > 1:
                                    # Navigate to specific slide
                                    slide_url = f"{clean_url}?img_index={slide_num}"
                                    page.goto(slide_url, wait_until='domcontentloaded')
                                    _time.sleep(1)
                                else:
                                    # Single image post
                                    page.goto(clean_url)
                                    _time.sleep(1)
                                
                                # Take screenshot of article
                                art = page.locator('article').first
                                
                                if slide_count == 1:
                                    out_file = str(profile_posts_dir / f"{post_id}_screenshot.png")
                                else:
                                    out_file = str(profile_posts_dir / f"{post_id}_slide_{slide_num}.png")
                                
                                if art and art.is_visible():
                                    art.screenshot(path=out_file)
                                else:
                                    page.screenshot(path=out_file)
                                
                                screenshots_saved.append(out_file)
                                print(f"[Scraper]   ✅ Slide {slide_num}/{slide_count} -> {Path(out_file).name}")
                                
                            except Exception as e:
                                print(f"[Scraper]   ❌ Slide {slide_num} error: {e}")
                        
                        # =============================================
                        # SAVE METADATA JSON
                        # =============================================
                        metadata = {
                            'id': post_id,
                            'url': clean_url,
                            'post_url': clean_url,
                            'handle': handle,
                            'scraped_at': datetime.utcnow().isoformat(),
                            'slide_count': slide_count,
                            'screenshots': [Path(s).name for s in screenshots_saved],
                            'processed': True
                        }
                        
                        # Try to extract caption from page
                        try:
                            caption_el = page.locator('article h1, article span[class*="Caption"]').first
                            if caption_el and caption_el.is_visible():
                                metadata['caption'] = caption_el.text_content()[:500]
                                metadata['text'] = metadata['caption']
                        except Exception:
                            pass
                        
                        json_path = profile_data_dir / f"{post_id}.json"
                        with open(json_path, 'w', encoding='utf-8') as f:
                            json.dump(metadata, f, indent=2, ensure_ascii=False)
                        
                        print(f"[Scraper] 💾 Metadata saved: {json_path.name}")
                        print(f"[Scraper] ✅ Done! {len(screenshots_saved)} screenshots saved for {slide_count} slides")
                        
                        ctx.close()
                    
                except Exception as e:
                    import traceback
                    print(f"[Scraper] ❌ Error: {e}")
                    traceback.print_exc()
            
            # Start in thread
            thread = threading.Thread(target=run_single_post_scraper, daemon=True)
            thread.start()
            
            msg = f'Scraper uruchomiony dla posta {post_id}'
            if is_new_profile:
                msg += f' (utworzono nowy profil: @{handle})'
            msg += '. Sprawdź konsolę serwera.'
            
            self.send_json({
                'status': 'started',
                'message': msg,
                'post_id': post_id,
                'handle': handle,
                'profile_id': f'ig-{handle}',
                'new_profile': is_new_profile
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_error_json(str(e), 500)
    
    def handle_delete_post(self, prefixed_profile, post_id):
        """Delete entire post (move to backup)."""
        try:
            platform, profile = self.parse_profile_id(prefixed_profile)
            config = self.get_platform_config(platform)
            data_dir = config['data_dir']
            evidence_dir = config['evidence_dir']
            posts_subdir = config['posts_subdir']
            ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            backup_subdir = BACKUP_DIR / f"post_delete_{ts}"
            backup_subdir.mkdir(parents=True, exist_ok=True)
            
            # Move JSON
            json_path = data_dir / profile / f"{post_id}.json"
            if json_path.exists():
                shutil.move(str(json_path), str(backup_subdir / json_path.name))
            
            # Move screenshots
            if posts_subdir:
                posts_dir = evidence_dir / profile / posts_subdir
            else:
                posts_dir = evidence_dir / profile
            if posts_dir.exists():
                for f in posts_dir.iterdir():
                    if f.is_file() and post_id in f.stem:
                        shutil.move(str(f), str(backup_subdir / f.name))
            
            self.send_json({'status': 'success', 'backup': str(backup_subdir)})
        except Exception as e:
            self.send_error_json(str(e), 500)
    
    def handle_delete_screenshot(self, prefixed_profile, post_id):
        """Delete a single screenshot (move to backup)."""
        try:
            platform, profile = self.parse_profile_id(prefixed_profile)
            config = self.get_platform_config(platform)
            data_dir = config['data_dir']
            evidence_dir = config['evidence_dir']
            posts_subdir = config['posts_subdir']
            
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            filename = data.get('filename')
            if not filename:
                self.send_error_json('Missing filename', 400)
                return
            
            file_path = evidence_dir / profile / posts_subdir / filename
            if not file_path.exists():
                self.send_error_json('File not found', 404)
                return
            
            # Move to backup
            ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            backup_subdir = BACKUP_DIR / f"screenshot_remove_{ts}"
            backup_subdir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(backup_subdir / filename))
            
            # Update metadata
            json_path = data_dir / profile / f"{post_id}.json"
            if json_path.exists():
                with open(json_path, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                
                # Remove from screenshots list
                if 'screenshots' in meta and isinstance(meta['screenshots'], list):
                    if filename in meta['screenshots']:
                        meta['screenshots'].remove(filename)
                
                # Remove single screenshot field
                if 'screenshot' in meta and meta['screenshot'] == filename:
                    del meta['screenshot']
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(meta, f, indent=2, ensure_ascii=False)
            
            self.send_json({'status': 'success'})
        except Exception as e:
            self.send_error_json(str(e), 500)
    
    def handle_upload(self, prefixed_profile, post_id):
        """Handle file upload."""
        try:
            platform, profile = self.parse_profile_id(prefixed_profile)
            config = self.get_platform_config(platform)
            data_dir = config['data_dir']
            evidence_dir = config['evidence_dir']
            posts_subdir = config['posts_subdir']
            
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' not in content_type:
                self.send_error_json('Invalid content type', 400)
                return
            
            # Parse multipart form data
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    'REQUEST_METHOD': 'POST',
                    'CONTENT_TYPE': content_type
                }
            )
            
            if posts_subdir:
                posts_dir = evidence_dir / profile / posts_subdir
            else:
                posts_dir = evidence_dir / profile
            posts_dir.mkdir(parents=True, exist_ok=True)
            
            uploaded_files = []
            
            # Handle file(s)
            files = form.getlist('files')
            if not files:
                files = [form['files']] if 'files' in form else []
            
            for item in files:
                if item.filename:
                    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
                    ext = Path(item.filename).suffix or '.jpg'
                    new_name = f"{post_id}_added_{ts}{ext}"
                    
                    dest_path = posts_dir / new_name
                    with open(dest_path, 'wb') as f:
                        f.write(item.file.read())
                    
                    uploaded_files.append(new_name)
            
            # Update metadata
            if uploaded_files:
                json_path = data_dir / profile / f"{post_id}.json"
                if json_path.exists():
                    with open(json_path, 'r', encoding='utf-8') as f:
                        meta = json.load(f)
                    
                    # Migrate to screenshots list if needed
                    if 'screenshots' not in meta or not isinstance(meta['screenshots'], list):
                        meta['screenshots'] = []
                        if 'screenshot' in meta and meta['screenshot']:
                            meta['screenshots'].append(meta['screenshot'])
                    
                    meta['screenshots'].extend(uploaded_files)
                    
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(meta, f, indent=2, ensure_ascii=False)
            
            self.send_json({'status': 'success', 'uploaded': uploaded_files})
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_error_json(str(e), 500)
    
    # ==========================================
    # GRAPH API HANDLERS
    # ==========================================
    
    def _load_graph_nodes(self):
        """Load graph nodes from JSON file."""
        if GRAPH_NODES_FILE.exists():
            with open(GRAPH_NODES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_graph_nodes(self, nodes):
        """Save graph nodes to JSON file."""
        with open(GRAPH_NODES_FILE, 'w', encoding='utf-8') as f:
            json.dump(nodes, f, indent=2, ensure_ascii=False)
    
    def _load_graph_edges(self):
        """Load graph edges from JSON file."""
        if GRAPH_EDGES_FILE.exists():
            with open(GRAPH_EDGES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def _save_graph_edges(self, edges):
        """Save graph edges to JSON file."""
        with open(GRAPH_EDGES_FILE, 'w', encoding='utf-8') as f:
            json.dump(edges, f, indent=2, ensure_ascii=False)
    
    def handle_get_entity_types(self):
        """Get available entity types."""
        self.send_json(ENTITY_TYPES)
    
    def handle_get_relationship_types(self):
        """Get available relationship types."""
        self.send_json(RELATIONSHIP_TYPES)
    
    def handle_get_graph_nodes(self):
        """Get all graph nodes with optional filtering."""
        try:
            nodes = self._load_graph_nodes()
            
            # Parse query params for filtering
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            
            # Filter by entity_type if specified
            entity_type = params.get('type', [None])[0]
            if entity_type:
                nodes = [n for n in nodes if n.get('entity_type') == entity_type]
            
            # Filter by search term
            search = params.get('search', [None])[0]
            if search:
                search_lower = search.lower()
                nodes = [n for n in nodes if 
                    search_lower in n.get('name', '').lower() or
                    search_lower in n.get('id', '').lower() or
                    search_lower in n.get('description', '').lower()
                ]
            
            # Add entity type metadata
            for node in nodes:
                et = node.get('entity_type', 'unknown')
                if et in ENTITY_TYPES:
                    node['_icon'] = ENTITY_TYPES[et]['icon']
                    node['_color'] = ENTITY_TYPES[et]['color']
                    node['_label'] = ENTITY_TYPES[et]['label']
            
            self.send_json(nodes)
        except Exception as e:
            self.send_error_json(str(e), 500)
    
    def handle_get_graph_edges(self):
        """Get all graph edges with optional filtering."""
        try:
            edges = self._load_graph_edges()
            
            # Parse query params
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            
            # Filter by relationship type
            rel_type = params.get('type', [None])[0]
            if rel_type:
                edges = [e for e in edges if e.get('relationship_type') == rel_type]
            
            # Filter by node ID (source or target)
            node_id = params.get('node', [None])[0]
            if node_id:
                edges = [e for e in edges if 
                    e.get('source_id') == node_id or e.get('target_id') == node_id
                ]
            
            self.send_json(edges)
        except Exception as e:
            self.send_error_json(str(e), 500)
    
    def handle_get_graph_node(self, node_id):
        """Get a single graph node by ID."""
        try:
            nodes = self._load_graph_nodes()
            node = next((n for n in nodes if n.get('id') == node_id), None)
            
            if not node:
                self.send_error_json('Node not found', 404)
                return
            
            # Add entity type metadata
            et = node.get('entity_type', 'unknown')
            if et in ENTITY_TYPES:
                node['_icon'] = ENTITY_TYPES[et]['icon']
                node['_color'] = ENTITY_TYPES[et]['color']
                node['_label'] = ENTITY_TYPES[et]['label']
            
            self.send_json(node)
        except Exception as e:
            self.send_error_json(str(e), 500)
    
    def handle_get_node_edges(self, node_id):
        """Get all edges connected to a node."""
        try:
            edges = self._load_graph_edges()
            node_edges = [e for e in edges if 
                e.get('source_id') == node_id or e.get('target_id') == node_id
            ]
            self.send_json(node_edges)
        except Exception as e:
            self.send_error_json(str(e), 500)
    
    def handle_search_graph(self, search_query):
        """Search nodes in Neo4j graph."""
        try:
            if not search_query or len(search_query) < 2:
                self.send_json([])
                return
            
            neo4j_client = get_neo4j_client()
            
            with neo4j_client.driver.session() as session:
                # Search in node names, descriptions, and IDs
                # Use 'term' instead of 'query' to avoid argument name conflict in session.run()
                result = session.run("""
                    MATCH (n)
                    WHERE toLower(n.name) CONTAINS toLower($term)
                       OR toLower(n.description) CONTAINS toLower($term)
                       OR toLower(n.id) CONTAINS toLower($term)
                    RETURN n.id as id, n.name as name, n.entity_type as entity_type,
                           n.description as description, labels(n) as labels
                    LIMIT 50
                """, term=search_query)
                
                nodes = []
                for record in result:
                    node = {
                        'id': record['id'],
                        'name': record['name'] or 'Unknown',
                        'entity_type': record['entity_type'],
                        'description': record['description'],
                        'labels': record['labels']
                    }
                    
                    # Add icon based on entity type
                    et = node.get('entity_type', 'unknown')
                    if et in ENTITY_TYPES:
                        node['icon'] = ENTITY_TYPES[et]['icon']
                        node['color'] = ENTITY_TYPES[et]['color']
                    else:
                        node['icon'] = 'fas fa-circle'
                        node['color'] = '#888'
                    
                    nodes.append(node)
                
                print(f"[SEARCH] Found {len(nodes)} results for query: {search_query}")
                self.send_json(nodes)
        except Exception as e:
            print(f"[SEARCH ERROR] {e}")
            self.send_error_json(str(e), 500)
    
    def handle_create_graph_node(self):
        """Create a new graph node."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            # Validate required fields
            entity_type = data.get('entity_type')
            name = data.get('name', '').strip()
            
            if not entity_type:
                self.send_error_json('Missing entity_type', 400)
                return
            if not name:
                self.send_error_json('Missing name', 400)
                return
            
            # Generate ID if not provided
            node_id = data.get('id', '').strip()
            if not node_id:
                import re
                # Generate ID based on type and name
                prefix_map = {
                    'person': 'ent',
                    'organization': 'org',
                    'profile': 'profile',
                    'event': 'evt',
                    'post': 'post',
                    'page': 'website',
                    'group': 'group',
                    'channel': 'channel',
                    'symbol': 'sym'
                }
                prefix = prefix_map.get(entity_type, 'node')
                name_slug = re.sub(r'[^a-z0-9]+', '-', name.lower())[:30]
                node_id = f"{prefix}-{name_slug}"
            
            # Load existing nodes
            nodes = self._load_graph_nodes()
            
            # Check for duplicate ID
            if any(n.get('id') == node_id for n in nodes):
                # Add suffix to make unique
                node_id = f"{node_id}-{str(uuid.uuid4())[:6]}"
            
            # Create node
            new_node = {
                'id': node_id,
                'name': name,
                'entity_type': entity_type,
                'description': data.get('description', ''),
                'country': data.get('country', 'PL'),
                'first_seen': datetime.utcnow().strftime('%Y-%m-%d'),
                'notes': data.get('notes', '')
            }
            
            # Add type-specific fields
            if entity_type == 'person':
                if data.get('roles'):
                    new_node['roles'] = data['roles']
            elif entity_type == 'event':
                if data.get('date_start'):
                    new_node['date_start'] = data['date_start']
                if data.get('date_end'):
                    new_node['date_end'] = data['date_end']
                if data.get('location'):
                    new_node['location'] = data['location']
            elif entity_type == 'profile':
                if data.get('platform'):
                    new_node['platform'] = data['platform']
                if data.get('url'):
                    new_node['url'] = data['url']
                if data.get('handle'):
                    new_node['handle'] = data['handle']
            elif entity_type in ('page', 'channel'):
                if data.get('url'):
                    new_node['url'] = data['url']
            elif entity_type == 'post':
                if data.get('url'):
                    new_node['url'] = data['url']
                if data.get('platform'):
                    new_node['platform'] = data['platform']
                if data.get('date_posted'):
                    new_node['date_posted'] = data['date_posted']
            
            # Add any extra fields
            for key, value in data.items():
                if key not in new_node and key not in ['_icon', '_color', '_label']:
                    new_node[key] = value
            
            nodes.append(new_node)
            self._save_graph_nodes(nodes)
            
            self.send_json({
                'status': 'success',
                'node': new_node
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_error_json(str(e), 500)
    
    def handle_update_graph_node(self, node_id):
        """Update an existing graph node."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            nodes = self._load_graph_nodes()
            node_idx = next((i for i, n in enumerate(nodes) if n.get('id') == node_id), None)
            
            if node_idx is None:
                self.send_error_json('Node not found', 404)
                return
            
            # Update fields
            for key, value in data.items():
                if key != 'id' and key not in ['_icon', '_color', '_label']:
                    nodes[node_idx][key] = value
            
            self._save_graph_nodes(nodes)
            
            self.send_json({
                'status': 'success',
                'node': nodes[node_idx]
            })
        except Exception as e:
            self.send_error_json(str(e), 500)
    
    def handle_delete_graph_node(self, node_id):
        """Delete a graph node (and related edges)."""
        try:
            nodes = self._load_graph_nodes()
            edges = self._load_graph_edges()
            
            # Find node
            node_idx = next((i for i, n in enumerate(nodes) if n.get('id') == node_id), None)
            if node_idx is None:
                self.send_error_json('Node not found', 404)
                return
            
            deleted_node = nodes.pop(node_idx)
            
            # Remove related edges
            edges_before = len(edges)
            edges = [e for e in edges if 
                e.get('source_id') != node_id and e.get('target_id') != node_id
            ]
            edges_removed = edges_before - len(edges)
            
            self._save_graph_nodes(nodes)
            self._save_graph_edges(edges)
            
            self.send_json({
                'status': 'success',
                'deleted_node': deleted_node,
                'edges_removed': edges_removed
            })
        except Exception as e:
            self.send_error_json(str(e), 500)
    
    def handle_create_graph_edge(self):
        """Create a new graph edge (relationship)."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            source_id = data.get('source_id')
            target_id = data.get('target_id')
            relationship_type = data.get('relationship_type')
            
            if not source_id or not target_id or not relationship_type:
                self.send_error_json('Missing source_id, target_id, or relationship_type', 400)
                return
            
            # Load nodes to get names
            nodes = self._load_graph_nodes()
            source_node = next((n for n in nodes if n.get('id') == source_id), None)
            target_node = next((n for n in nodes if n.get('id') == target_id), None)
            
            if not source_node:
                self.send_error_json(f'Source node not found: {source_id}', 404)
                return
            if not target_node:
                self.send_error_json(f'Target node not found: {target_id}', 404)
                return
            
            edges = self._load_graph_edges()
            
            # Generate edge ID
            edge_id = data.get('id') or f"rel-{source_id}-{target_id}-{relationship_type.lower()}"
            
            # Check for duplicate
            if any(e.get('id') == edge_id for e in edges):
                edge_id = f"{edge_id}-{str(uuid.uuid4())[:6]}"
            
            new_edge = {
                'id': edge_id,
                'source_id': source_id,
                'source_name': source_node.get('name', ''),
                'target_id': target_id,
                'target_name': target_node.get('name', ''),
                'relationship_type': relationship_type,
                'date': data.get('date', datetime.utcnow().strftime('%Y-%m-%d')),
                'confidence': data.get('confidence', 1.0),
                'evidence': data.get('evidence', '')
            }
            
            edges.append(new_edge)
            self._save_graph_edges(edges)
            
            self.send_json({
                'status': 'success',
                'edge': new_edge
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_error_json(str(e), 500)
    
    def handle_sync_to_neo4j(self):
        """Sync graph data to Neo4j database by running load_to_neo4j.py script."""
        try:
            import subprocess
            script_path = PROJECT_ROOT / "scripts" / "load_to_neo4j.py"
            
            if not script_path.exists():
                self.send_error_json('Script load_to_neo4j.py not found', 404)
                return
            
            # Run the script
            result = subprocess.run(
                ['python', str(script_path)],
                cwd=str(PROJECT_ROOT),
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                self.send_json({
                    'status': 'success',
                    'message': 'Synchronizacja zakończona pomyślnie',
                    'output': result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
                })
            else:
                self.send_json({
                    'status': 'error',
                    'message': 'Błąd synchronizacji',
                    'error': result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr,
                    'output': result.stdout[-1000:] if len(result.stdout) > 1000 else result.stdout
                }, status=500)
        except subprocess.TimeoutExpired:
            self.send_error_json('Synchronizacja przekroczyła limit czasu (60s)', 500)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.send_error_json(str(e), 500)
    
    def handle_update_graph_edge(self, edge_id):
        """Update an existing graph edge."""
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))
            
            edges = self._load_graph_edges()
            edge_idx = next((i for i, e in enumerate(edges) if e.get('id') == edge_id), None)
            
            if edge_idx is None:
                self.send_error_json('Edge not found', 404)
                return
            
            # Update fields
            for key, value in data.items():
                if key != 'id':
                    edges[edge_idx][key] = value
            
            self._save_graph_edges(edges)
            
            self.send_json({
                'status': 'success',
                'edge': edges[edge_idx]
            })
        except Exception as e:
            self.send_error_json(str(e), 500)
    
    def handle_delete_graph_edge(self, edge_id):
        """Delete a graph edge."""
        try:
            edges = self._load_graph_edges()
            edge_idx = next((i for i, e in enumerate(edges) if e.get('id') == edge_id), None)
            
            if edge_idx is None:
                self.send_error_json('Edge not found', 404)
                return
            
            deleted_edge = edges.pop(edge_idx)
            self._save_graph_edges(edges)
            
            self.send_json({
                'status': 'success',
                'deleted_edge': deleted_edge
            })
        except Exception as e:
            self.send_error_json(str(e), 500)
    
    def handle_data_file(self):
        """Serve static data files (evidence images)."""
        try:
            # Parse path: /data/evidence/instagram/profile/posts/file.jpg
            path = urllib.parse.unquote(self.path)
            # Remove /data prefix and map to actual path
            relative_path = path[5:]  # Remove /data
            file_path = PROJECT_ROOT / "data" / relative_path.lstrip('/')
            
            if not file_path.exists():
                self.send_error(404, 'File not found')
                return
            
            # Determine content type
            ext = file_path.suffix.lower()
            content_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.heic': 'image/heic'
            }
            content_type = content_types.get(ext, 'application/octet-stream')
            
            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', file_path.stat().st_size)
            self.send_header('Cache-Control', 'max-age=3600')
            self.end_headers()
            
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        except Exception as e:
            self.send_error(500, str(e))


def run_server():
    """Start the server."""
    print(f"=" * 60)
    print(f"Social Media Manager - Backend Server")
    print(f"=" * 60)
    print(f"Platforms supported:")
    for name, cfg in PLATFORMS.items():
        print(f"  {cfg['prefix']}-* : {name.capitalize()}")
        print(f"      Data: {cfg['data_dir']}")
        print(f"      Evidence: {cfg['evidence_dir']}")
    print(f"=" * 60)
    print(f"Web directory: {WEB_DIR}")
    print(f"=" * 60)
    print(f"Server running at: http://localhost:{PORT}")
    print(f"Open: http://localhost:{PORT}/")
    print(f"=" * 60)
    
    # ThreadingTCPServer for handling multiple concurrent requests
    class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True
        daemon_threads = True
    
    with ThreadedTCPServer(("", PORT), SocialMediaAPIHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    run_server()
