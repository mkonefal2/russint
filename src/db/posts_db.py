#!/usr/bin/env python3
"""
DuckDB database manager for social media posts.
Single source of truth for raw post data.
"""

import duckdb
from pathlib import Path
from typing import List, Dict, Optional, Any
import json

DB_PATH = Path(__file__).parent.parent.parent / "data" / "posts.duckdb"


class PostsDB:
    """Manager for posts database."""
    
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = None
        self._init_schema()
    
    def _init_schema(self):
        """Initialize database schema."""
        conn = duckdb.connect(str(self.db_path))
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id VARCHAR PRIMARY KEY,
                platform VARCHAR NOT NULL,
                handle VARCHAR NOT NULL,
                post_url VARCHAR,
                text TEXT,
                raw_text_preview TEXT,
                date_posted TIMESTAMP,
                screenshot_path VARCHAR,
                metadata JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for fast queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_platform ON posts(platform)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_handle ON posts(handle)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_date ON posts(date_posted)")
        
        conn.close()
    
    def get_connection(self):
        """Get database connection."""
        if self.conn is None:
            self.conn = duckdb.connect(str(self.db_path))
        return self.conn
    
    def insert_post(self, post_data: Dict[str, Any]) -> bool:
        """Insert or update a post."""
        conn = self.get_connection()
        
        try:
            conn.execute("""
                INSERT OR REPLACE INTO posts (
                    id, platform, handle, post_url, text, raw_text_preview,
                    date_posted, screenshot_path, metadata, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, [
                post_data.get('id'),
                post_data.get('platform'),
                post_data.get('handle'),
                post_data.get('post_url'),
                post_data.get('text'),
                post_data.get('raw_text_preview'),
                post_data.get('date_posted'),
                post_data.get('screenshot'),
                json.dumps(post_data.get('metadata', {}))
            ])
            return True
        except Exception as e:
            print(f"Error inserting post {post_data.get('id')}: {e}")
            return False
    
    def get_posts(self, platform: Optional[str] = None, 
                  handle: Optional[str] = None,
                  limit: int = 100, offset: int = 0) -> List[Dict]:
        """Get posts with optional filters."""
        conn = self.get_connection()
        
        query = "SELECT * FROM posts WHERE 1=1"
        params = []
        
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        
        if handle:
            query += " AND handle = ?"
            params.append(handle)
        
        query += " ORDER BY date_posted DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        result = conn.execute(query, params).fetchall()
        columns = [desc[0] for desc in conn.description]
        
        return [dict(zip(columns, row)) for row in result]
    
    def get_post_by_id(self, post_id: str) -> Optional[Dict]:
        """Get single post by ID."""
        conn = self.get_connection()
        result = conn.execute("SELECT * FROM posts WHERE id = ?", [post_id]).fetchone()
        
        if result:
            columns = [desc[0] for desc in conn.description]
            return dict(zip(columns, result))
        return None
    
    def count_posts(self, platform: Optional[str] = None, 
                    handle: Optional[str] = None) -> int:
        """Count posts with optional filters."""
        conn = self.get_connection()
        
        query = "SELECT COUNT(*) FROM posts WHERE 1=1"
        params = []
        
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        
        if handle:
            query += " AND handle = ?"
            params.append(handle)
        
        return conn.execute(query, params).fetchone()[0]
    
    def get_handles(self, platform: Optional[str] = None) -> List[str]:
        """Get list of unique handles."""
        conn = self.get_connection()
        
        query = "SELECT DISTINCT handle FROM posts WHERE 1=1"
        params = []
        
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        
        query += " ORDER BY handle"
        
        result = conn.execute(query, params).fetchall()
        return [row[0] for row in result]
    
    def search_posts(self, search_text: str, limit: int = 50) -> List[Dict]:
        """Full-text search in posts."""
        conn = self.get_connection()
        
        query = """
            SELECT * FROM posts 
            WHERE text LIKE ? OR raw_text_preview LIKE ?
            ORDER BY date_posted DESC
            LIMIT ?
        """
        search_pattern = f"%{search_text}%"
        result = conn.execute(query, [search_pattern, search_pattern, limit]).fetchall()
        columns = [desc[0] for desc in conn.description]
        
        return [dict(zip(columns, row)) for row in result]
    
    def close(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


def get_posts_db() -> PostsDB:
    """Get singleton PostsDB instance."""
    return PostsDB()
