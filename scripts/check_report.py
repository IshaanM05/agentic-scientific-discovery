"""Fail if a report has a claim without a source id or cites an id that does not exist.

    python scripts/check_report.py docs/REPORT_STEEL.md docs/REPORT_LABLOOP.md

The report names its own run directory in the first line (`<!-- asd-report: {...} -->`); the source registry is
rebuilt from that directory and the repo files, never read from the report. Checks: source tag on every claim line,
one sentence per tag, every id exists, numbers (>= 2 digits or decimals) and quoted spans appear in the cited
sources, no hidden-truth key. It checks provenance, not whether a sentence is a fair reading of its source.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from asd import report as R  # noqa: E402


def check_file(path) -> list[str]:
    md = Path(path).read_text(encoding="utf-8")
    m = re.search(r"<!-- asd-report: (\{.*?\}) -->", md)
    if not m:
        return [f"{path}: no asd-report manifest on the first line"]
    man = json.loads(m.group(1))
    try:
        src = R.load_sources(man["kind"], man["run_dir"])
    except (R.ReportError, FileNotFoundError, KeyError) as e:
        return [f"{path}: cannot rebuild sources: {e}"]
    return [f"{path}:{n}: {p}: {l}" for n, p, l in R.check_markdown(md, src)]


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    bad = [x for f in argv for x in check_file(f)]
    for b in bad:
        print(b)
    print(f"{'FAIL' if bad else 'OK'}: {len(argv)} report(s), {len(bad)} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
