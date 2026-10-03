"""Score a live-run ledger and write its run record: python scripts/score_ledger.py <ledger> <out.json> <arm> <seed>"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from asd.replay import experiments_to_k_hits  # noqa: E402

led, out, arm, seed = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
rows = [json.loads(x) for x in open(led, encoding="utf-8")]
hits = [r["budget_used"] for r in rows if r["is_hit"]]
rec = {"arm": arm, "seed": seed, "budget": 60, "n_init": 5, "spent": len(rows), "hits_by_step": hits,
       "n_hits": len(hits), "order": [r["id"] for r in rows],
       "to_k": {str(k): experiments_to_k_hits(hits, k, 60) for k in (1, 3, 5)}}
Path(out).write_text(json.dumps(rec))
print(json.dumps({k: rec[k] for k in ("arm", "seed", "spent", "n_hits", "to_k")}))
