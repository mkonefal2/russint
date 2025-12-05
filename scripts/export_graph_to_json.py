#!/usr/bin/env python3
"""Export Neo4j graph to a JSON file for offline editing.

Usage:
    python scripts/export_graph_to_json.py [--limit N] [--out path]

Creates a file under `data/processed/graph_exports/` with timestamp.
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


def fetch_graph(limit=1000):
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

                def proc(node):
                    nid = None
                    try:
                        nid = node.get('id')
                    except Exception:
                        nid = str(node.id)
                    props = dict(node)
                    labels = list(node.labels) if hasattr(node, 'labels') else []
                    return nid or str(node.id), {
                        'id': nid or str(node.id),
                        'name': props.get('name') or props.get('title') or str(node.id),
                        'group': labels[0] if labels else 'Unknown',
                        'properties': props
                    }

                src_id, src_node = proc(n)
                tgt_id, tgt_node = proc(m)
                if src_id not in nodes:
                    nodes[src_id] = src_node
                if tgt_id not in nodes:
                    nodes[tgt_id] = tgt_node

                links.append({
                    'source': src_id,
                    'target': tgt_id,
                    'type': r.type,
                    'properties': dict(r)
                })
    finally:
        driver.close()

    return {'nodes': list(nodes.values()), 'links': links}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=2000)
    parser.add_argument('--out', type=str, default=None)
    args = parser.parse_args()

    data = fetch_graph(limit=args.limit)

    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    out_dir = Path('data/processed/graph_exports')
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = args.out or f'export_graph_{ts}.json'
    out_path = out_dir / filename

    payload = {
        'meta': {
            'exported_at': datetime.utcnow().isoformat() + 'Z',
            'limit': args.limit
        },
        'nodes': data['nodes'],
        'links': data['links']
    }

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)

    print(f'Exported graph to: {out_path}')


if __name__ == '__main__':
    main()
