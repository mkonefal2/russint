#!/usr/bin/env python3
"""
Scan evidence folders and match image files to node IDs (1:1).
Generates an incremental JSON in `src/ui/static/data/processed/graph_increments/`
so the loader can assign `image`/`screenshot` properties to nodes.
"""
import json
import os
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent

# Candidate locations for node seed file
NODE_FILES = [
    ROOT / 'src' / 'ui' / 'static' / 'data' / 'raw' / 'graph_nodes.json',
    ROOT / 'static' / 'data' / 'raw' / 'graph_nodes.json',
    ROOT / 'data' / 'raw' / 'graph_nodes.json',
]

EVIDENCE_DIRS = [
    ROOT / 'data' / 'evidence',
    ROOT / 'src' / 'ui' / 'static' / 'data' / 'evidence',
    ROOT / 'static' / 'data' / 'evidence',
]

OUT_DIR = ROOT / 'src' / 'ui' / 'static' / 'data' / 'processed' / 'graph_increments'
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_node_ids():
    for p in NODE_FILES:
        if p.exists():
            with p.open('r', encoding='utf-8') as f:
                data = json.load(f)
                ids = set()
                # graph_nodes.json may be a list of nodes
                if isinstance(data, list):
                    for n in data:
                        if 'id' in n:
                            ids.add(n['id'])
                elif isinstance(data, dict):
                    # maybe wrapped
                    for n in data.get('nodes', []):
                        if 'id' in n:
                            ids.add(n['id'])
                print(f"Loaded {len(ids)} node ids from {p}")
                return ids
    print('No graph_nodes.json found in candidates; proceeding with empty node list')
    return set()


def find_evidence_files():
    files = []
    for d in EVIDENCE_DIRS:
        if d.exists():
            for p in d.rglob('*'):
                if p.is_file():
                    files.append(p)
    return files


def find_raw_facebook_jsons():
    raws = []
    fb_root = ROOT / 'static' / 'data' / 'raw' / 'facebook'
    # also check src/ui/static mirror and data/raw
    candidates = [
        fb_root,
        ROOT / 'data' / 'raw' / 'facebook',
        ROOT / 'src' / 'ui' / 'static' / 'data' / 'raw' / 'facebook'
    ]
    for d in candidates:
        if d and d.exists():
            for p in d.rglob('*.json'):
                raws.append(p)
    return raws


def normalize_repo_path(path: Path) -> str:
    # Return path starting with 'data/...', used in JSON properties
    s = str(path).replace('\\', '/')
    idx = s.find('/data/')
    if idx != -1:
        return s[idx+1:]
    # fallback: try to find 'evidence/' segment and prepend 'data'
    idx = s.find('/evidence/')
    if idx != -1:
        return 'data' + s[idx:]
    return s


def main():
    node_ids = load_node_ids()
    files = find_evidence_files()
    fb_jsons = find_raw_facebook_jsons()

    matches = []
    unmatched = []

    for f in files:
        name = f.stem  # filename without extension
        norm = normalize_repo_path(f)

        # direct id match
        if name in node_ids:
            # decide property by folder
            prop = 'image' if '/evidence/symbols/' in norm or '/evidence/symbols' in norm else 'screenshot'
            matches.append({'id': name, prop: norm})
            continue

        # for facebook screenshots, filenames often start with fb_{handle}_{postid}
        if name.startswith('fb_') and name in node_ids:
            matches.append({'id': name, 'screenshot': norm})
            continue

        # try alternative: some node ids use hyphens while filenames use underscores
        alt = name.replace('_', '-')
        if alt in node_ids:
            prop = 'image' if '/evidence/symbols/' in norm else 'screenshot'
            matches.append({'id': alt, prop: norm})
            continue

        # try removing common prefixes like fb_, page-, profile- etc.
        for prefix in ('fb_', 'page-', 'profile-', 'post-'):
            if name.startswith(prefix):
                candidate = name[len(prefix):]
                if candidate in node_ids:
                    prop = 'image' if '/evidence/symbols/' in norm else 'screenshot'
                    matches.append({'id': candidate, prop: norm})
                    break
        else:
            unmatched.append(norm)

    # Build incremental JSON
    ts = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
    out = {
        'meta': {
            'source': 'match_images_by_id.py',
            'generated_at': datetime.utcnow().isoformat(),
            'matches_count': len(matches)
        },
        'nodes': [],
        'edges': []
    }

    # Convert matches into node objects suitable for incremental loader
    for m in matches:
        node = {'id': m['id']}
        if 'image' in m:
            node['image'] = m['image']
        if 'screenshot' in m:
            node['screenshot'] = m['screenshot']
        out['nodes'].append(node)

    # Also parse raw facebook JSONs to ensure posts link to their screenshots
    parsed = 0
    for j in fb_jsons:
        try:
            with j.open('r', encoding='utf-8') as fh:
                jd = json.load(fh)
                pid = jd.get('id')
                shot = jd.get('screenshot') or jd.get('file')
                if pid and shot:
                    # normalize separators
                    shot = shot.replace('\\', '/').lstrip('/')
                    # create entries for post-, id, and screenshot- nodes
                    post_node = {'id': f'post-{pid}', 'evidence': shot}
                    bare_node = {'id': pid, 'screenshot': shot}
                    screenshot_node = {'id': f'screenshot-{pid}', 'file': shot}
                    out['nodes'].append(post_node)
                    out['nodes'].append(bare_node)
                    out['nodes'].append(screenshot_node)
                    parsed += 1
        except Exception:
            continue

    if parsed:
        out['meta']['fb_jsons_parsed'] = parsed

    out_path = OUT_DIR / f'analysis_match_images_by_id_{ts}.json'
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f'Wrote incremental file: {out_path} (matches: {len(matches)}, unmatched files: {len(unmatched)})')
    if unmatched:
        print('\nSome evidence files were not matched to node ids (sample 20):')
        for u in unmatched[:20]:
            print(' -', u)


if __name__ == '__main__':
    main()
