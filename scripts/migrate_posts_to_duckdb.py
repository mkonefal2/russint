#!/usr/bin/env python3
"""
Migrate all posts from JSON files to DuckDB.
Creates the single source of truth for post data.

Usage:
  python scripts/migrate_posts_to_duckdb.py --dry-run
  python scripts/migrate_posts_to_duckdb.py --apply
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from db.posts_db import get_posts_db

ROOT = Path(__file__).parent.parent
RAW_DIR = ROOT / 'data' / 'raw'


def parse_date(date_str):
    """Parse date string to datetime."""
    if not date_str:
        return None
    
    # Try common formats
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d.%m.%Y', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    return None


def collect_posts_from_json():
    """Collect all posts from raw JSON files."""
    posts = []
    
    # Facebook posts
    fb_dir = RAW_DIR / 'facebook'
    if fb_dir.exists():
        for handle_dir in fb_dir.iterdir():
            if not handle_dir.is_dir():
                continue
            handle = handle_dir.name
            
            for json_file in handle_dir.glob('*.json'):
                try:
                    data = json.loads(json_file.read_text(encoding='utf-8'))
                    post_id = json_file.stem
                    
                    post = {
                        'id': post_id,
                        'platform': 'facebook',
                        'handle': handle,
                        'post_url': data.get('post_url'),
                        'text': data.get('text'),
                        'raw_text_preview': data.get('raw_text_preview'),
                        'date_posted': parse_date(data.get('date_posted')),
                        'screenshot': data.get('screenshot'),
                        'metadata': {
                            'reactions': data.get('reactions'),
                            'comments': data.get('comments'),
                            'shares': data.get('shares'),
                            'image': data.get('image'),
                            'video': data.get('video')
                        }
                    }
                    posts.append(post)
                except Exception as e:
                    print(f"Error reading {json_file}: {e}")
    
    # Instagram posts
    ig_dir = RAW_DIR / 'instagram'
    if ig_dir.exists():
        for handle_dir in ig_dir.iterdir():
            if not handle_dir.is_dir():
                continue
            handle = handle_dir.name
            
            for json_file in handle_dir.glob('*.json'):
                try:
                    data = json.loads(json_file.read_text(encoding='utf-8'))
                    post_id = json_file.stem
                    
                    post = {
                        'id': post_id,
                        'platform': 'instagram',
                        'handle': handle,
                        'post_url': data.get('post_url'),
                        'text': data.get('caption'),
                        'raw_text_preview': data.get('caption'),
                        'date_posted': parse_date(data.get('date_posted')),
                        'screenshot': data.get('screenshot'),
                        'metadata': {
                            'likes': data.get('likes'),
                            'comments_count': data.get('comments_count'),
                            'media_type': data.get('media_type'),
                            'media_url': data.get('media_url')
                        }
                    }
                    posts.append(post)
                except Exception as e:
                    print(f"Error reading {json_file}: {e}")
    
    # Telegram posts
    tg_dir = RAW_DIR / 'telegram'
    if tg_dir.exists():
        for channel_dir in tg_dir.iterdir():
            if not channel_dir.is_dir():
                continue
            channel = channel_dir.name
            
            for json_file in channel_dir.glob('*.json'):
                try:
                    data = json.loads(json_file.read_text(encoding='utf-8'))
                    post_id = json_file.stem
                    
                    post = {
                        'id': post_id,
                        'platform': 'telegram',
                        'handle': channel,
                        'post_url': data.get('message_url'),
                        'text': data.get('text'),
                        'raw_text_preview': data.get('text'),
                        'date_posted': parse_date(data.get('date')),
                        'screenshot': data.get('screenshot'),
                        'metadata': {
                            'views': data.get('views'),
                            'forwards': data.get('forwards'),
                            'media': data.get('media')
                        }
                    }
                    posts.append(post)
                except Exception as e:
                    print(f"Error reading {json_file}: {e}")
    
    return posts


def migrate_posts(dry_run: bool = True):
    """Migrate posts to DuckDB."""
    print("🔍 Collecting posts from JSON files...")
    posts = collect_posts_from_json()
    
    if not posts:
        print("❌ No posts found in raw directories.")
        return
    
    print(f"\n📊 Found {len(posts)} posts:")
    
    # Group by platform
    by_platform = {}
    for p in posts:
        platform = p['platform']
        by_platform[platform] = by_platform.get(platform, 0) + 1
    
    for platform, count in sorted(by_platform.items()):
        print(f"   {platform}: {count}")
    
    if dry_run:
        print("\n⚠️  DRY RUN: Would migrate these posts to DuckDB.")
        print("   Run with --apply to actually migrate.")
        return
    
    # Migrate to DuckDB
    print("\n🚀 Migrating posts to DuckDB...")
    db = get_posts_db()
    
    success_count = 0
    for post in posts:
        if db.insert_post(post):
            success_count += 1
    
    db.close()
    
    print(f"\n✅ Migrated {success_count}/{len(posts)} posts to DuckDB.")
    print(f"   Database: {db.db_path}")


def main():
    parser = argparse.ArgumentParser(description='Migrate posts from JSON to DuckDB.')
    parser.add_argument('--dry-run', action='store_true', help='Preview migration')
    parser.add_argument('--apply', action='store_true', help='Actually migrate')
    args = parser.parse_args()

    if args.apply:
        migrate_posts(dry_run=False)
    else:
        migrate_posts(dry_run=True)


if __name__ == '__main__':
    main()
