#!/usr/bin/env python3
"""
Remove orphaned unknown nodes from Neo4j.
These are nodes with no relationships that clutter the database.

Usage:
  python scripts/remove_orphaned_unknowns.py --dry-run
  python scripts/remove_orphaned_unknowns.py --apply
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from graph.neo4j_client import get_client

def remove_orphaned_unknowns(dry_run: bool = True):
    client = get_client()
    
    with client.driver.session() as session:
        # Count orphaned unknowns
        result = session.run("""
            MATCH (n)
            WHERE (coalesce(toLower(n.entity_type),'unknown') = 'unknown' 
               OR coalesce(n.name,'Unknown') = 'Unknown')
            AND NOT (n)-[]-()
            RETURN count(n) as orphaned_count
        """)
        
        count = result.single()['orphaned_count']
        
        if count == 0:
            print("✅ No orphaned unknown nodes found.")
            return
        
        print(f"\n🗑️  Found {count} orphaned unknown nodes.")
        
        # Sample before deletion
        result = session.run("""
            MATCH (n)
            WHERE (coalesce(toLower(n.entity_type),'unknown') = 'unknown' 
               OR coalesce(n.name,'Unknown') = 'Unknown')
            AND NOT (n)-[]-()
            RETURN n.id as id, n.name as name
            LIMIT 10
        """)
        
        samples = list(result)
        print("\n📝 Sample nodes to be deleted:")
        for rec in samples:
            print(f"   {rec['id']} | {rec['name']}")
        
        if dry_run:
            print(f"\n⚠️  DRY RUN: Would delete {count} orphaned unknown nodes.")
            print("   Run with --apply to actually delete them.")
            return
        
        # Delete orphaned unknowns
        result = session.run("""
            MATCH (n)
            WHERE (coalesce(toLower(n.entity_type),'unknown') = 'unknown' 
               OR coalesce(n.name,'Unknown') = 'Unknown')
            AND NOT (n)-[]-()
            DELETE n
            RETURN count(n) as deleted_count
        """)
        
        deleted = result.single()['deleted_count']
        print(f"\n✅ Deleted {deleted} orphaned unknown nodes.")

def main():
    parser = argparse.ArgumentParser(description='Remove orphaned unknown nodes from Neo4j.')
    parser.add_argument('--dry-run', action='store_true', help='Preview what would be deleted')
    parser.add_argument('--apply', action='store_true', help='Actually delete the nodes')
    args = parser.parse_args()

    if args.apply:
        remove_orphaned_unknowns(dry_run=False)
    else:
        remove_orphaned_unknowns(dry_run=True)

if __name__ == '__main__':
    main()
