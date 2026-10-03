"""Apply the judge to analysis records of existing runs; writes runs/<run>/judge.jsonl (originals untouched)."""
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from asd.cli_llm import Throttled  # noqa: E402
from asd.judge import judge  # noqa: E402


def main(runs):
    for run in runs:
        d = pathlib.Path("runs") / run
        rec = [json.loads(x) for x in open(d / "record.jsonl")]
        hyps, out = {}, []
        for e in rec:
            if e["kind"] == "hypothesis":
                hyps[e["id"]] = e
            elif e["kind"] == "analysis":
                try:
                    v = judge(e, hyps.get(e["hypothesis_id"]), e["value"])
                except Throttled as ex:
                    print("THROTTLED, stop:", ex)
                    return 2
                out.append({"record_id": f"judge-{e['record_id']}", "kind": "judge_verdict",
                            "run_id": e.get("run_id"), **v})
        if out:
            (d / "judge.jsonl").write_text("\n".join(json.dumps(x) for x in out) + "\n")
        print(run, len(out))


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or ["t011", "live1", "live2"]))
