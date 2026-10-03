"""One offline arena tournament (seed 0, NAMED steel domain). Writes runs/arena/*.jsonl.
Named, not blinded: hypotheses are about composition regions (feature names + wt% ranges), which blinding would
destroy; memorisation of matbench_steels is a stated caveat, and the prompt never names the dataset."""
import json
import pathlib
import sys

from asd import arena as A, schemas as S, tools
from asd.cli_llm import STATS, Throttled


def main(seed=0):
    out = pathlib.Path("runs/arena")
    out.mkdir(parents=True, exist_ok=True)
    tools.reset(seed=seed, budget=60, run_dir=out / "lit_run", run_id="arena")
    try:
        hyps = A.generate(seed)
        for h in hyps:
            h["novelty"] = A.novelty(h, tools.literature_search)
            S.check(h, S.ARENA_HYP)
        crits = A.critique(hyps, seed)
        elo, matches = A.elo_round(hyps, crits, seed)
    except Throttled as e:
        print("THROTTLED, stop:", e)
        return 2

    def w(n, rows):
        (out / n).write_text("".join(json.dumps(r) + "\n" for r in rows))

    w("hypotheses.jsonl", hyps)
    w("critiques.jsonl", crits)
    w("elo.jsonl", [{"id": k, "elo": round(v, 1)} for k, v in sorted(elo.items(), key=lambda x: -x[1])]
      + [{"match": m} for m in matches])
    print(len(hyps), "hypotheses", STATS)


if __name__ == "__main__":
    sys.exit(main())
