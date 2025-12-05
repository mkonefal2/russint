**PUSH WORKFLOW: Edit graph via JSON and apply to Neo4j**

Purpose
- Ensure all manual edits are done against an exported JSON snapshot, reviewed, and then applied to Neo4j with an automated backup.

Files / Tools
- `scripts/export_graph_to_json.py` — exports current Neo4j graph to `data/processed/graph_exports/export_graph_*.json`.
- `scripts/apply_json_to_neo4j.py` — creates a DB backup and applies the provided JSON to Neo4j (MERGE nodes/relationships by `id`).

Recommended steps
1. Export current DB:

```bash
python scripts/export_graph_to_json.py --limit 5000
```

This writes `data/processed/graph_exports/export_graph_<timestamp>.json`.

2. Edit exported JSON
- Open the exported file. You can add/remove nodes or update `properties`.
- To mark a node as the main node, add a property in the node's `properties`, for example:

```json
{
  "id": "node-123",
  "name": "Some Node",
  "group": "Profile",
  "properties": {
    "name": "Some Node",
    "main": true
  }
}
```

3. Apply changes to DB (creates backup automatically):

```bash
python scripts/apply_json_to_neo4j.py data/processed/graph_exports/export_graph_20251204T224136Z.json
```

The script writes a backup file to `data/backup/neo4j_backup_<timestamp>.json` before applying edits.

Notes
- The scripts use Neo4j credentials from environment variables (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`) or a `.env` file.
- The apply script uses `MERGE` by `id` and will `SET` properties on matched nodes; relationships are merged by matching nodes with the given `id` fields.
- This workflow is intended to be explicit and repeatable. Always export first, edit the exported JSON, then apply.

If you want, I can also:
- Add a small CLI wrapper that opens the last export file in your editor.
- Add a confirmation prompt before `apply_json_to_neo4j.py` runs.
