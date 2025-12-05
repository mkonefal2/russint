#!/usr/bin/env python3
"""Apply a prepared JSON file (exported by export_graph_to_json.py) back to Neo4j.

This script will:
 - create/merge nodes by `id` and set properties
 - create relationships between nodes
 - make a backup export before applying changes

Usage:
    python scripts/apply_json_to_neo4j.py path/to/export.json
"""
import os
import json
from pathlib import Path
from datetime import datetime
import argparse
from neo4j import GraphDatabase
from dotenv import load_dotenv


def get_driver():
    load_dotenv()
    uri = os.getenv('NEO4J_URI')
    user = os.getenv('NEO4J_USER')
    password = os.getenv('NEO4J_PASSWORD')
    if not uri or not user or not password:
        raise RuntimeError('Missing Neo4j credentials in environment')
    return GraphDatabase.driver(uri, auth=(user, password))


def backup_current_graph(limit=5000):
    # Use the export script's logic via a simple query
    driver = get_driver()
    nodes = {}
    links = []
    try:
        with driver.session() as session:
            query = """
            MATCH (n)-[r]->(m)
            RETURN n, r, m
            LIMIT $limit
            """
            result = session.run(query, limit=limit)
            for record in result:
                n = record['n']
                m = record['m']
                r = record['r']
                nid = n.get('id') if 'id' in n else str(n.id)
                mid = m.get('id') if 'id' in m else str(m.id)
                if nid not in nodes:
                    nodes[nid] = {'id': nid, 'properties': dict(n), 'group': list(n.labels)[0] if hasattr(n, 'labels') and n.labels else 'Unknown'}
                if mid not in nodes:
                    nodes[mid] = {'id': mid, 'properties': dict(m), 'group': list(m.labels)[0] if hasattr(m, 'labels') and m.labels else 'Unknown'}
                links.append({'source': nid, 'target': mid, 'type': r.type, 'properties': dict(r)})
    finally:
        driver.close()

    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    out_dir = Path('data/backup')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f'neo4j_backup_{ts}.json'
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump({'meta': {'backup_at': datetime.utcnow().isoformat() + 'Z'}, 'nodes': list(nodes.values()), 'links': links}, f, indent=2, ensure_ascii=False)
    print(f'Backup written to: {out_path}')
    return out_path


def apply_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    nodes = data.get('nodes', [])
    links = data.get('links', [])

    driver = get_driver()
    try:
        with driver.session() as session:
            # Create/merge nodes
            for n in nodes:
                nid = n.get('id')
                props = n.get('properties', {})
                label = n.get('group') or 'Entity'
                # Use parameterized query
                q = f"MERGE (x:{label} {{id: $id}}) SET x += $props"
                session.run(q, id=nid, props=props)

            # Create relationships
            for r in links:
                s = r.get('source')
                t = r.get('target')
                rtype = r.get('type') or 'RELATED'
                props = r.get('properties', {})
                q = """
                MATCH (a {id: $s}), (b {id: $t})
                MERGE (a)-[rel:%s]->(b)
                SET rel += $props
                """ % rtype
                session.run(q, s=s, t=t, props=props)

    finally:
        driver.close()

    print('Applied JSON to Neo4j successfully')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('jsonpath', type=str, help='Path to exported JSON to apply')
    args = parser.parse_args()

    src = Path(args.jsonpath)
    if not src.exists():
        print('File not found:', src)
        return

    print('Creating backup of current DB...')
    backup_current_graph()
    print('Applying changes from:', src)
    apply_json(src)


if __name__ == '__main__':
    main()
