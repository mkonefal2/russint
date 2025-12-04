import json
from pathlib import Path

BASE = Path(__file__).parent.parent
INCR_DIR = BASE / 'data' / 'processed' / 'graph_increments'
RAW_DIR = BASE / 'data' / 'raw'
RAW_DIR.mkdir(parents=True, exist_ok=True)

entity_map = {}
relationships = []

for p in INCR_DIR.glob('analysis_*.json'):
    try:
        with p.open('r', encoding='utf-8') as f:
            doc = json.load(f)
    except Exception as e:
        print(f"Skipping {p}: {e}")
        continue

    nodes = doc.get('nodes') or []
    edges = doc.get('edges') or []

    for n in nodes:
        nid = n.get('id')
        if not nid:
            continue
        # merge: prefer existing keys, but update with new ones
        if nid in entity_map:
            existing = entity_map[nid]
            # update fields that are missing
            for k, v in n.items():
                if k not in existing or existing.get(k) in (None, ''):
                    existing[k] = v
        else:
            entity_map[nid] = n

    for e in edges:
        relationships.append(e)

entities = list(entity_map.values())

ENT_FILE = RAW_DIR / 'entities.json'
REL_FILE = RAW_DIR / 'relationships.json'

with ENT_FILE.open('w', encoding='utf-8') as f:
    json.dump(entities, f, ensure_ascii=False, indent=2)

with REL_FILE.open('w', encoding='utf-8') as f:
    json.dump(relationships, f, ensure_ascii=False, indent=2)

print(f'Wygenerowano {len(entities)} entities -> {ENT_FILE}')
print(f'Wygenerowano {len(relationships)} relationships -> {REL_FILE}')
