"""Write data/t009_probe_ids.json: 15 hits + 5 non-hits drawn with random.Random(0). Run once, commit before any LLM call."""
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asd.replay import HIT_THRESHOLD, load_pool  # noqa: E402

rows = load_pool()
hits = [i for i, r in enumerate(rows) if r["yield strength"] >= HIT_THRESHOLD]
non = [i for i, r in enumerate(rows) if r["yield strength"] < HIT_THRESHOLD]
pick = sorted(random.Random(0).sample(non, 5))
out = {"index_space": "row index in load_pool() order (asd/replay.py), not shuffled cXXX ids",
       "hits": hits, "non_hits": pick, "ids": sorted(hits + pick)}
Path("data/t009_probe_ids.json").write_text(json.dumps(out, indent=1))
print(len(hits), len(pick))
