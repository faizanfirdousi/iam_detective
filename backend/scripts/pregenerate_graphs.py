"""pregenerate_graphs.py — One-time script to warm the graph cache to disk.

Run from the backend/ directory:
    python scripts/pregenerate_graphs.py

This calls each DO AI Agent 5 times (4 domain passes + synthesis), merges the
result with the static schema, and writes {case_id}-graph.json to
app/data/case_schemas/. On the next FastAPI startup those files are loaded
automatically, avoiding the 90-180 s cold-build time.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys

# Make sure the app package is importable when running from backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from app.services.graph_extractor import build_full_case_graph  # noqa: E402
from app.services.graph_merger import merge_graph_with_schema   # noqa: E402

CASES = ["zodiac-killer", "aarushi-talwar", "oj-simpson"]
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "data", "case_schemas")


async def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    for case_id in CASES:
        print(f"\n{'='*60}")
        print(f"→ Building graph for: {case_id}")
        print(f"{'='*60}")
        try:
            ai_graph = await build_full_case_graph(case_id)
            merged = merge_graph_with_schema(case_id, ai_graph)
            out_path = os.path.join(OUT_DIR, f"{case_id}-graph.json")
            with open(out_path, "w") as f:
                json.dump(merged, f, indent=2)
            n_nodes = len(merged["nodes"])
            n_edges = len(merged["edges"])
            print(f"  ✓ {n_nodes} nodes, {n_edges} edges → {out_path}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            import traceback
            traceback.print_exc()

    print("\nDone. Restart FastAPI to load the pre-generated graphs.")


if __name__ == "__main__":
    asyncio.run(main())
