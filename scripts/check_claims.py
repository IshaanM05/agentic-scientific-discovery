"""Claims-versus-evidence audit: every published number must match a committed result file.

Reads docs/claims.yaml. For each claim it (1) loads the source file, (2) extracts the value at
the key path (JSON/JSONL) or by regex (text files), (3) compares it with the documented number
within the tolerance, (4) checks the exact claim text still appears in the document and that the
text actually contains the number. Then it scans the documents for numbers that no claim covers
and prints them as warnings (never a failure). Offline; no model calls.

    python scripts/check_claims.py                      # table, exit 1 on any failure
    python scripts/check_claims.py --md docs/CLAIMS_AUDIT.md
    python scripts/check_claims.py --root /other/tree   # audit a different checkout

Key paths use "/" between segments; a numeric segment indexes a list, the final segment "#len"
returns the length of a list. Text sources use `pattern`: a regex whose group 1 is the number.
Optional claim fields: `op` (eq default, or lt/le/gt/ge: the source must be below/above the value,
for statements like "p<0.001"), `scale` (multiply the source, e.g. 100 for a percentage), `count: true`
(text sources: the value is the number of regex matches), `text_number: false` (the text states
the value in words, e.g. "none worse"), `branch` (the source is committed only on
that branch; its text may be too). A claim whose document is absent from the tree is SKIP (a document can live on another
branch), as is one with `branch` whose source is absent; a present document whose source file is absent
is otherwise a failure. --strict makes SKIP a failure too.
"""
from __future__ import annotations

import argparse
import gzip
import json
import re
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
FAIL = {"MISMATCH", "TEXT-MISSING", "NUMBER-NOT-IN-TEXT", "SOURCE-MISSING", "KEY-ERROR"}
# a number token: optional sign (only after start/space/bracket), digits, optional decimals, optional %
NUM_RE = re.compile(r"(?:(?<![\w.])[+\-−])?\d+(?:\.\d+)?(?:[eE][+\-]?\d+)?%?")
SCAN_RE = re.compile(r"(?<![\w.#/-])[+\-−]?\d+\.\d+%?|(?<![\w.#/-])\d+(?:\.\d+)?%|\bn\s?=\s?\d+|\b\d+/\d+\b")


# inline code, URLs, file links, arXiv/DOI ids, model and tool versions are not results
MASK_RE = re.compile(r"`[^`]*`|https?://\S+|\(\S+\.(?:png|json|md|py)\)|arXiv:[\d.v]+|doi:?\s?[\w./-]+|"
                     r"(?:Sonnet|Haiku|Opus|omnigent|Apache)\s[\d.]+|\bv?\d+\.\d+\.\d+\b")


def _num(tok: str) -> float:
    return float(tok.replace("−", "-").replace("+", "").rstrip("%"))


def norm_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def text_numbers(text: str) -> list[float]:
    out = []
    text = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text)  # 2,772 -> 2772
    for m in NUM_RE.finditer(text):
        try:
            out.append(_num(m.group(0)))
        except ValueError:
            pass
    return out


def load_source(path: Path):
    if path.suffix == ".gz":
        return json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return json.loads(path.read_text(encoding="utf-8"))


def extract(claim: dict, root: Path):
    """Return the source value for a claim, or raise KeyError/ValueError/FileNotFoundError."""
    src = root / claim["source"]
    if not src.is_file():
        raise FileNotFoundError(claim["source"])
    if "pattern" in claim:
        body = src.read_text(encoding="utf-8")
        if claim.get("count"):
            return len(re.findall(claim["pattern"], body))
        m = re.search(claim["pattern"], body)
        if not m:
            raise KeyError(f"pattern not found: {claim['pattern']}")
        return _num(m.group(1))
    node = load_source(src)
    segs = [s for s in str(claim["key"]).split("/") if s != ""]
    for i, seg in enumerate(segs):
        if seg is None:
            continue
        if seg == "#len" and i == len(segs) - 1:
            return len(node)
        if isinstance(node, list):
            node = node[int(seg)]
        elif isinstance(node, dict):
            # a JSON key may itself contain "/": take the longest joined run of segments that exists
            for j in range(len(segs), i, -1):
                joined = "/".join(segs[i:j])
                if joined in node:
                    node, skip_to = node[joined], j
                    break
            else:
                raise KeyError(f"missing key '{seg}' in {claim['key']}")
            if skip_to != i + 1:
                segs[i + 1:skip_to] = [None] * (skip_to - i - 1)
        else:
            raise KeyError(f"cannot descend into scalar at '{seg}'")
    if isinstance(node, bool) or not isinstance(node, (int, float)):
        raise ValueError(f"value at {claim['key']} is not a number: {node!r}")
    return node


def check_claim(claim: dict, root: Path, strict: bool = False) -> dict:
    cid = claim["id"]
    res = {"id": cid, "doc": claim["doc"], "doc_value": claim["value"], "source": claim["source"],
           "key": claim.get("key", claim.get("pattern", "")), "src_value": None, "status": "OK", "note": ""}
    doc = root / claim["doc"]
    if not doc.is_file():
        res["status"] = "SKIP"
        res["note"] = "document not present in this tree"
        return res
    tol = float(claim.get("tol", 0.0))
    try:
        res["src_value"] = extract(claim, root)
    except FileNotFoundError:
        if claim.get("branch"):
            res.update(status="SKIP", note=f"source is committed on branch {claim['branch']}")
        else:
            res.update(status="SOURCE-MISSING", note="source file not committed")
        return res
    except (KeyError, ValueError, IndexError) as e:
        res.update(status="KEY-ERROR", note=str(e))
        return res
    res["src_value"] = res["src_value"] * float(claim.get("scale", 1))
    op, sv, dv = claim.get("op", "eq"), res["src_value"], float(claim["value"])
    ok = {"eq": abs(sv - dv) <= tol + 1e-9, "lt": sv < dv, "le": sv <= dv, "gt": sv > dv, "ge": sv >= dv}[op]
    if not ok:
        res.update(status="MISMATCH",
                   note=f"document says {op} {claim['value']}, source has {sv:.6g} (tol {tol})")
        return res
    if norm_ws(claim["text"]) not in norm_ws(doc.read_text(encoding="utf-8")):
        if claim.get("branch"):
            res.update(status="SKIP", note=f"text is committed on branch {claim['branch']}")
        else:
            res.update(status="TEXT-MISSING", note="claim text not found in document (edited or moved?)")
        return res
    if claim.get("text_number", True) and not any(
            abs(n - float(claim["value"])) <= tol + 1e-9 for n in text_numbers(claim["text"])):
        res.update(status="NUMBER-NOT-IN-TEXT", note="claim text does not contain the claimed value")
    return res


def _covered_spans(text: str, claims: list[dict], doc: str) -> list[tuple[int, int]]:
    spans = []
    for c in claims:
        if c["doc"] != doc:
            continue
        pat = r"\s+".join(re.escape(w) for w in c["text"].split())
        spans += [m.span() for m in re.finditer(pat, text)]
    return spans


def scan_uncovered(root: Path, claims: list[dict], docs: list[str]) -> list[tuple[str, int, str, str]]:
    """Numeric tokens in the scanned docs that no claim text covers: (doc, line, token, context)."""
    out = []
    for d in docs:
        p = root / d
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        spans = _covered_spans(text, claims, d)
        in_fence, offset = False, 0
        for lineno, line in enumerate(text.splitlines(keepends=True), 1):
            start, offset = offset, offset + len(line)
            if line.lstrip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence or re.match(r"\s*\|[\s:|-]+\|\s*$", line):
                continue
            # blank out inline code and URLs so paths, commits and links are not scanned
            masked = re.sub(MASK_RE, lambda m: " " * len(m.group(0)), line)
            for m in SCAN_RE.finditer(masked):
                a, b = start + m.start(), start + m.end()
                if any(s <= a and b <= e for s, e in spans):
                    continue
                ctx = norm_ws(line)
                out.append((d, lineno, m.group(0), ctx[:110]))
    return out


def load_claims(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("claims"), list):
        raise ValueError(f"{path}: expected a mapping with a 'claims' list")
    seen = set()
    for c in data["claims"]:
        missing = [k for k in ("id", "text", "doc", "value", "source") if k not in c]
        if missing:
            raise ValueError(f"claim {c.get('id', '?')}: missing {missing}")
        if "key" not in c and "pattern" not in c:
            raise ValueError(f"claim {c['id']}: needs 'key' or 'pattern'")
        if c.get("op", "eq") not in ("eq", "lt", "le", "gt", "ge"):
            raise ValueError(f"claim {c['id']}: bad op {c['op']!r}")
        if c["id"] in seen:
            raise ValueError(f"duplicate claim id {c['id']}")
        seen.add(c["id"])
    data.setdefault("unsourced", [])
    data.setdefault("notes", [])
    data.setdefault("scan", ["README.md"])
    return data


def run(claims_path: Path, root: Path, strict: bool = False):
    data = load_claims(claims_path)
    results = [check_claim(c, root) for c in data["claims"]]
    warnings = scan_uncovered(root, data["claims"], data["scan"])
    failed = [r for r in results if r["status"] in FAIL or (strict and r["status"] == "SKIP")]
    return data, results, warnings, failed


def fmt_table(results: list[dict]) -> str:
    rows = [("id", "status", "doc", "source", "doc_value", "src_value")]
    for r in results:
        rows.append((r["id"], r["status"], str(r["doc_value"]),
                     "" if r["src_value"] is None else f"{r['src_value']:.6g}", r["source"], r["note"]))
    rows[0] = ("id", "status", "doc_value", "src_value", "source", "note")
    w = [max(len(x[i]) for x in rows) for i in range(5)]
    return "\n".join("  ".join(x[i].ljust(w[i]) for i in range(5)) + "  " + x[5] for x in rows).rstrip()


def render_md(data, results, warnings, failed, claims_path: str, label: str = "") -> str:
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    L = ["# Claims audit", "",
         "Generated by `python scripts/check_claims.py --md docs/CLAIMS_AUDIT.md`; do not edit by hand. "
         f"Claims are listed in `{claims_path}`: each ties a number printed in a document to a committed "
         "result file and a key path, with a tolerance. The checker also verifies the claim text still "
         "appears in the document. Offline, no model calls.", "",
         "Summary: " + ", ".join(f"{v} {k}" for k, v in sorted(counts.items())) +
         f"; {len(data['unsourced'])} listed as unsourced; {len(warnings)} uncovered numbers (warnings).", ""]
    if label:
        L[2:2] = [f"Tree audited: {label}.", ""]
    L += ["## Mismatches and failures", ""]
    if failed:
        for r in failed:
            L.append(f"- `{r['id']}` ({r['status']}) in `{r['doc']}`: {r['note'] or 'see table'}. "
                     f"Source: `{r['source']}` `{r['key']}`.")
    else:
        L.append("None: every sourced claim matches its source within tolerance.")
    L += ["", "## Notes for the lead", ""] + [f"- {n}" for n in data["notes"]] if data["notes"] else []
    L += ["", "## All claims", "", "| id | status | document | doc value | source value | source | key |",
          "|---|---|---|---|---|---|---|"]
    for r in results:
        sv = "" if r["src_value"] is None else f"{r['src_value']:.6g}"
        L.append(f"| {r['id']} | {r['status']} | `{r['doc']}` | {r['doc_value']} | {sv} | `{r['source']}` | `{r['key']}` |")
    L += ["", "## Unsourced (no committed file holds the number)", ""]
    L += [f"- `{u['id']}` in `{u['doc']}`: \"{u['text']}\". {u['reason']}" for u in data["unsourced"]] or ["None."]
    L += ["", "## Numbers in scanned documents not covered by any claim (warnings)", ""]
    L += [f"- `{d}:{n}` `{tok}`: {ctx}" for d, n, tok, ctx in warnings] or ["None."]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--claims", default=None, help="claims file (default: <root>/docs/claims.yaml)")
    ap.add_argument("--root", default=str(REPO), help="repository root to audit")
    ap.add_argument("--md", default=None, help="write the audit as markdown to this path")
    ap.add_argument("--label", default="", help="describe the audited tree in the markdown report")
    ap.add_argument("--strict", action="store_true", help="treat SKIP (absent document) as failure")
    a = ap.parse_args(argv)
    root = Path(a.root)
    claims_path = Path(a.claims) if a.claims else root / "docs" / "claims.yaml"
    data, results, warnings, failed = run(claims_path, root, a.strict)
    print(fmt_table(results))
    print(f"\n{len(results)} claims: {len(failed)} failed, "
          f"{sum(r['status'] == 'SKIP' for r in results)} skipped, {len(data['unsourced'])} unsourced")
    for d, n, tok, ctx in warnings:
        print(f"WARNING uncovered number {tok!r} at {d}:{n}: {ctx}")
    if a.md:
        Path(a.md).write_text(render_md(data, results, warnings, failed, "docs/claims.yaml", a.label), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
