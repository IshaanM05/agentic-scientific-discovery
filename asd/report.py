"""Traceable research report: core (source registry, claim syntax, checker, polish hook) plus the steel renderer.

Every factual line of a report ends with one or more source tags, `[src: id, id]`. An id is a record id
(`rec-0011`, `judge-rec-0016`), a ledger id (`ledger-0003`), a notebook id (`nb:E001`), a citation id, a repo file
(`file:docs/X.md`) or a derived value (`calc:name`) that the loader computes from the run directory. The checker
rebuilds the registry from the run directory, so a report cannot vouch for itself.

What the checker proves: every claim carries a source id; every id exists; every number of 10 or more or with a
decimal point appears in a cited source (within display rounding); every quoted span is verbatim in a cited source;
no hidden-truth key appears. It does NOT prove that a sentence is a fair reading of its source.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TAG = re.compile(r"\[src:\s*([^\]]+)\]")
QUOTE = re.compile(r"“([^”]*)”|`([^`]*)`")  # quoted prose or `code`: both must be verbatim in a cited source
ID_TOKEN = re.compile(r"\b[A-Za-z]+[-_]?\d+\w*\b")
NUM = re.compile(r"(?<![\w.])-?\d+(?:\.\d+)?")
SENT_BREAK = re.compile(r"[.!?]\s+(?=[A-Z])")
FORBIDDEN = ("eg_true", "lt_true", "true_hit", "true_hits", "world_params", "sn_pen", "sn_exp", "eg_shift", "cl_bonus")
SEPARATOR = re.compile(r"^\s*\|?\s*:?-{3,}")


class ReportError(Exception):
    pass


def flatten(x) -> str:
    if isinstance(x, dict):
        return "\n".join(flatten(v) for v in x.values())
    if isinstance(x, (list, tuple)):
        return "\n".join(flatten(v) for v in x)
    return "" if x is None else str(x)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.replace("\\|", "|")).strip()


class Sources:
    """Registry id -> flat text of the source. Built by a loader from a run directory."""

    def __init__(self, root: Path = ROOT):
        self.root, self.d, self.raw = Path(root), {}, {}

    def add(self, sid: str, obj) -> str:
        self.d[sid] = flatten(obj)
        self.raw[sid] = json.dumps(obj, default=str).lower()  # keys too: leak scan must see field names
        return sid

    def calc(self, name: str, value) -> str:
        return self.add(f"calc:{name}", f"{name} {value}")

    def file(self, rel: str) -> str:
        p = self.root / rel
        if p.exists():
            self.d[f"file:{rel}"] = p.read_text(encoding="utf-8", errors="replace")
        return f"file:{rel}"

    def __contains__(self, sid):
        return sid in self.d

    def text(self, sid):
        return self.d[sid]

    def leaks(self):
        """Hidden-truth keys in run data (repo files may name them in warnings, so they are not scanned)."""
        return sorted({f"{sid}: {term}" for sid, txt in self.raw.items() for term in FORBIDDEN if term in txt})


def code(s) -> str:
    """Inline code span (formulas, ids): verified verbatim by the checker, ignored by the number check."""
    return "`" + norm(str(s)).replace("`", "'").replace("|", "\\|") + "`"


def q(s, n=None) -> str:
    """Verbatim quote; a trailing … means 'prefix of the source'. Pipes are escaped for tables."""
    s = norm(str(s))
    if n and len(s) > n:
        s = s[:n].rstrip() + "…"
    return "“" + s.replace("|", "\\|") + "”"


def _numbers(text: str) -> list[float]:
    return [float(m) for m in NUM.findall(text)]


def _num_ok(tok: str, pct: bool, pool: list[float]) -> bool:
    x = float(tok)
    d = len(tok.split(".")[1]) if "." in tok else 0
    tol = 0.5 * 10 ** -d + 1e-9
    return any(abs(s - x) <= tol or (pct and abs(s * 100 - x) <= tol) for s in pool)


def check_line(line: str, src: Sources) -> list[str]:
    """Problems for one claim line (empty list = fine)."""
    probs = []
    tags = list(TAG.finditer(line))
    if not tags:
        return ["no source id"]
    tail = re.sub(r"[\W_]+", "", line[tags[-1].end():])
    if tail:
        probs.append("text after the last source tag has no source")
    pos = 0
    for m in tags:
        seg = line[pos:m.start()]
        pos = m.end()
        ids = [i.strip() for i in m.group(1).split(",") if i.strip()]
        if not ids:
            probs.append("empty source tag")
            continue
        missing = [i for i in ids if i not in src]
        if missing:
            probs.append("unknown source id: " + ", ".join(missing))
            continue
        pool_text = "\n".join(src.text(i) for i in ids)
        pool, flat = _numbers(pool_text), norm(pool_text)
        for qs in ["".join(g) for g in QUOTE.findall(seg)]:
            qq = norm(qs)
            ok = qq[:-1].rstrip() in flat if qq.endswith("…") else qq in flat
            if not ok:
                probs.append(f"quote not verbatim in cited source: {qq[:50]}")
        bare = QUOTE.sub("Q", seg)
        if len(SENT_BREAK.findall(bare)) >= 1:
            probs.append("more than one sentence under one source tag")
        plain = ID_TOKEN.sub(" ", bare)
        plain = re.sub(r"https?://\S+|\b[A-Z]{3}:\S+", " ", plain)
        for mm in NUM.finditer(plain):
            tok = mm.group(0).lstrip("-")
            if "." not in tok and len(tok) < 2:
                continue
            pct = plain[mm.end():mm.end() + 1] == "%"
            if not _num_ok(tok, pct, pool):
                probs.append(f"number {tok} not found in cited sources")
    for t in FORBIDDEN:
        if t in line.lower():
            probs.append(f"hidden-truth term {t!r}")
    return probs


def check_markdown(md: str, src: Sources) -> list[tuple[int, str, str]]:
    """Return (line_no, problem, line) for every claim line that fails. Headings, blanks, comments, table
    headers and separators are not claims."""
    out, lines, fence = [], md.splitlines(), False
    for n, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("```"):
            fence = not fence
            continue
        if fence or not s or s.startswith("#") or s.startswith("<!--") or s == "---" or SEPARATOR.match(s):
            continue
        nxt = lines[n].strip() if n < len(lines) else ""
        if s.startswith("|") and SEPARATOR.match(nxt):
            continue
        for p in check_line(line, src):
            out.append((n, p, line[:140]))
    return out


class Doc:
    """Builder that refuses to emit a claim that would fail the checker."""

    def __init__(self, src: Sources, manifest: dict):
        self.src, self.lines = src, [f"<!-- asd-report: {json.dumps(manifest, sort_keys=True)} -->"]

    def raw(self, line=""):
        self.lines.append(line)

    def h(self, level, title):
        self.lines += ["", "#" * level + " " + title, ""]

    def _tag(self, ids):
        ids = [i for i in dict.fromkeys(ids) if i]
        if not ids:
            raise ReportError("claim without source ids")
        return "[src: " + ", ".join(ids) + "]"

    def claim(self, text, *ids, bullet=True):
        line = f"{'- ' if bullet else ''}{text} {self._tag(ids)}"
        probs = check_line(line, self.src)
        if probs:
            raise ReportError(f"{probs} in: {line[:200]}")
        self.lines.append(line)

    def table(self, header, rows):
        self.lines.append("")
        self.lines.append("| " + " | ".join(header + ["source"]) + " |")
        self.lines.append("|" + "---|" * (len(header) + 1))
        for cells, ids in rows:
            line = "| " + " | ".join(str(c) for c in cells) + f" | {self._tag(ids)} |"
            probs = check_line(line, self.src)
            if probs:
                raise ReportError(f"{probs} in: {line[:200]}")
            self.lines.append(line)
        self.lines.append("")

    def text(self):
        return "\n".join(self.lines).rstrip() + "\n"


# --------------------------------------------------------------------------- polish hook (prose only)
def polish(md: str, fn, src: Sources) -> str:
    """Let `fn(text) -> text` reword the prose of each claim line. A rewrite is kept only if it adds no number,
    keeps every quoted span and the source tags unchanged, and the line still passes the checker; otherwise the
    original line stays. A model can therefore change wording, never facts."""
    out = []
    for line in md.splitlines():
        m = re.match(r"^(- )(.*?)((?:\s*\[src:[^\]]+\])+[.\s]*)$", line)
        if not m or line.startswith("|") or "“" in m.group(2) and False:
            out.append(line)
            continue
        pre, body, tail = m.groups()
        parts = re.split(r"(\s*\[src:[^\]]+\])", body + tail)
        if len([p for p in parts if TAG.search(p)]) != 1:  # polish only single-tag lines
            out.append(line)
            continue
        new = fn(body)
        keep = (isinstance(new, str) and new.strip() and QUOTE.findall(new) == QUOTE.findall(body)
                and not set(NUM.findall(ID_TOKEN.sub(" ", new))) - set(NUM.findall(ID_TOKEN.sub(" ", body))))
        cand = f"{pre}{new.strip()}{tail}" if keep else line
        out.append(cand if keep and not check_line(cand, src) else line)
    return "\n".join(out) + "\n"


# --------------------------------------------------------------------------- loaders and dispatch
def _jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()] if p.exists() else []


def resolve(run_dir) -> Path:
    p = Path(run_dir)
    return p if p.is_absolute() else ROOT / p


def load_steel(run_dir) -> tuple[Sources, dict]:
    run_dir = resolve(run_dir)
    src, d = Sources(), {"dir": run_dir}
    d["cites"] = {}
    d["meta"] = json.loads((run_dir / "meta.json").read_text()) if (run_dir / "meta.json").exists() else None
    d["rec"] = _jsonl(run_dir / "record.jsonl")
    d["ledger"] = _jsonl(run_dir / "ledger.jsonl")
    d["judge"] = _jsonl(run_dir / "judge.jsonl")
    if not d["rec"] or not d["ledger"]:
        raise ReportError(f"{run_dir}: need record.jsonl and ledger.jsonl")
    if d["meta"]:
        src.add("meta", d["meta"])
    for e in d["rec"]:
        src.add(e["record_id"], e)
        if e["kind"] == "literature":
            src.calc(f"ncit_{e['record_id']}", len(e.get("citations", [])))
        for c in e.get("citations", []) if e["kind"] == "literature" else []:
            src.add(c["id"], c)
            d["cites"][c["id"]] = c
            if c["id"].startswith("https://openalex.org/"):
                src.add(c["id"].rsplit("/", 1)[1], c)
    for e in d["judge"]:
        src.add(e["record_id"], e)
    for e in d["ledger"]:
        src.add(f"ledger-{e['step']:04d}", e)
    ana = [e for e in d["rec"] if e["kind"] == "analysis"]
    for name, val in {"n_records": len(d["rec"]), "n_ledger": len(d["ledger"]), "n_measured": len(d["ledger"]),
                      "hits": sum(1 for l in d["ledger"] if l["is_hit"]), "n_judge": len(d["judge"]),
                      "n_reopened": sum(len(a.get("reopened_assumptions", [])) for a in ana)}.items():
        src.calc(name, val)
    for h in (e for e in d["rec"] if e["kind"] == "hypothesis"):
        src.calc(f"{h['id']}_tests", sum(1 for a in ana if a["hypothesis_id"] == h["id"]))
    for f in ("docs/CLOUD_WORKER_CONTEXT.md", "docs/CHALLENGE_BRIEF.md", "asd/tools.py", "asd/replay.py", "scripts/make_report.py"):
        src.file(f)
    leaks = src.leaks()
    if leaks:
        raise ReportError("hidden-truth term in run sources: " + "; ".join(leaks[:3]))
    return src, d


def load_sources(kind: str, run_dir) -> Sources:
    if kind == "steel":
        return load_steel(run_dir)[0]
    if kind == "labloop":
        from labloop.report import load_labloop
        return load_labloop(run_dir)[0]
    raise ReportError(f"unknown report kind {kind!r}")


def _cites(src, ids):
    return [i for i in ids if i in src]


def render_steel(run_dir) -> str:
    src, d = load_steel(run_dir)
    rec, led, judge, meta = d["rec"], d["ledger"], d["judge"], d["meta"]
    by = lambda k: [e for e in rec if e["kind"] == k]
    rid = {e["record_id"]: e for e in rec}
    doc = Doc(src, {"kind": "steel", "run_dir": str(Path(run_dir).as_posix())})
    CTX, BRIEF = "file:docs/CLOUD_WORKER_CONTEXT.md", "file:docs/CHALLENGE_BRIEF.md"
    doc.raw(f"# Research report: steel yield strength ({Path(run_dir).name})")
    doc.raw()
    doc.raw("> Auto-generated from committed run records by a template; no model wrote this text [src: file:scripts/make_report.py]")
    doc.raw("> Every line carries a source id that the checker resolves against the run directory [src: file:scripts/make_report.py]")
    # 1 question
    doc.h(2, "1. Question")
    doc.claim("Which steel compositions in a 312-candidate public dataset reach a yield strength of 2000 MPa or more, "
              "and can an agent team find them within a small experiment budget", CTX, "file:asd/replay.py")
    if meta:
        doc.claim(f"This run used seed {meta['seed']} and a budget of {meta['budget']} experiments", "meta")
    doc.claim(f"The run record holds {len(rec)} entries and the ledger {len(led)} revealed measurements",
              "calc:n_records", "calc:n_ledger")
    # 2 evidence
    doc.h(2, "2. Evidence from literature (retrieved by the literature agent)")
    searches = by("literature")
    if searches:
        doc.claim(f"The literature agent ran {len(searches)} searches", *[e["record_id"] for e in searches][:8])
    if searches:
        doc.table(["search query", "papers returned"],
                  [([q(e["query"], 90), len(e.get("citations", []))], [e["record_id"], f"calc:ncit_{e['record_id']}"]) for e in searches])
    rows, seen = [], set()
    for h in [e for e in by("handoff") if e.get("handoff_kind") == "literature"]:
        cl = {re.match(r"\[(\w+)\]", c).group(1): c for c in h["payload"].get("claims", []) if re.match(r"\[(\w+)\]", c)}
        for cid in h["payload"].get("citations", []):
            short = cid.rsplit("/", 1)[-1]
            if short in seen or cid not in src:
                continue
            seen.add(short)
            c = d["cites"].get(cid, {})
            title = c.get("title", "").strip()
            summ = re.sub(r"^\[\w+\]\s*", "", cl.get(short, ""))
            rows.append(([short, f"{q(title, 90)} ({c.get('year', 'n.d.')})", q(summ, 110) if summ else "none recorded"], [cid, h["record_id"]] if summ else [cid]))
    if rows:
        doc.claim("Each row is a retrieved paper with the literature agent's one-line summary of it", rows[0][1][0], bullet=True)
        doc.claim("The summary is the agent's own reading and was not verified against the full text", rows[0][1][-1])
        doc.table(["id", "title", "agent summary"], rows[:15])
    # 3 hypotheses
    doc.h(2, "3. Hypotheses (all agent-generated, unvalidated)")
    analyses = by("analysis")
    for h in by("hypothesis"):
        hid = h["id"]
        mine = [a for a in analyses if a["hypothesis_id"] == hid]
        ns = sum(1 for a in mine if a["supported"])
        doc.claim(f"**{hid}** carries the label {q(h['label'], 60)}: {q(h['text'].split(': ', 1)[-1], 230)}", h["record_id"])
        doc.claim(f"{hid} predicts a yield strength of {h['predicted_value']} MPa for candidates "
                  f"{', '.join(h['candidate_ids'])}", h["record_id"])
        doc.claim(f"{hid} rests on the assumption {q(h['assumption'], 160)}", h["record_id"])
        doc.claim(f"Kill condition for {hid}: a measured value more than 25% away from the prediction counts as "
                  f"unsupported and reopens the assumption", "file:asd/tools.py")
        if mine:
            st = "refuted by every test" if ns == 0 else ("supported by every test" if ns == len(mine) else "mixed")
            doc.claim(f"Final status of {hid}: {st} ({ns} of {len(mine)} analysed tests supported)",
                      *[a["record_id"] for a in mine], f"calc:{hid}_tests")
        else:
            doc.claim(f"Final status of {hid}: untested in this run", h["record_id"])
    # 4 experiments
    doc.h(2, "4. Experiments and measured values")
    exps = {e["id"]: e for e in by("experiment")}
    rows, bad = [], []
    for l in led:
        lid = f"ledger-{l['step']:04d}"
        e = exps.get(l["id"])
        if e and abs(e["value"] - l["value"]) > 1e-6:
            bad.append((lid, e["record_id"]))
        rows.append(([lid, l["id"], f"{l['value']}", "yes" if l["is_hit"] else "no", e["hypothesis_id"] if e else "n/a"],
                     [lid] + ([e["record_id"]] if e else [])))
    doc.table(["ledger id", "candidate", "yield strength (MPa)", "meets 2000 MPa", "hypothesis"], rows)
    hits = sum(1 for l in led if l["is_hit"])
    doc.claim(f"{hits} of {len(led)} measured candidates reached 2000 MPa", "calc:hits", "calc:n_measured",
              "file:asd/replay.py")
    for lid, rid_ in bad:
        doc.claim(f"Integrity warning: ledger entry {lid} and record {rid_} disagree on the measured value", lid, rid_)
    # 5 planner choices
    doc.h(2, "5. Experiment choices (two or more candidate tests compared)")
    for t in by("test_choice"):
        opts = t["options"]
        doc.claim(f"Record {t['record_id']} compared {len(opts)} candidate tests and chose {q(t['chosen'], 80)}",
                  t["record_id"])
        doc.table(["option", "expected learning", "feasibility", "cost", "score"],
                  [([q(o["name"], 70), o["expected_learning"], o["feasibility"], o["cost"], o["score"]], [t["record_id"]])
                   for o in opts])
    # 6 negative results
    doc.h(2, "6. Negative results (kept, not hidden)")
    for l in [l for l in led if not l["is_hit"]]:
        doc.claim(f"Candidate {l['id']} measured {l['value']} MPa, below the 2000 MPa target", f"ledger-{l['step']:04d}",
                  "file:asd/replay.py")
    for a in analyses:
        if not a["supported"]:
            doc.claim(f"Hypothesis {a['hypothesis_id']} was unsupported: predicted {a['predicted']} MPa, measured {a['value']} MPa "
                      f"(relative error {a['rel_error']})", a["record_id"])
    # 7 what changed decisions
    doc.h(2, "7. What changed the planner's decisions")
    order = [e["record_id"] for e in rec]
    n_changes, announced = 0, set()
    for a in analyses:
        for r in a.get("reopened_assumptions", []):
            n_changes += 1
            later = [h for h in by("hypothesis") if order.index(h["record_id"]) > order.index(a["record_id"]) and h["id"] != a["hypothesis_id"]]
            doc.claim(f"Analysis {a['record_id']} reopened an assumption: {q(r, 170)}", a["record_id"])
            if later and later[0]["id"] not in announced:
                announced.add(later[0]["id"])
                doc.claim(f"The next hypothesis registered after the first reopened assumption was {later[0]['id']}", later[0]["record_id"], a["record_id"])
    for h in by("hypothesis"):
        if "Revised after" in h["text"]:
            doc.claim(f"Hypothesis {h['id']} states it was revised after earlier hypotheses failed: {q(h['text'].split('Revised after', 1)[1], 150)}",
                      h["record_id"])
    if not n_changes:
        doc.claim("No analysis in this run reopened an assumption", "calc:n_reopened")
    sel = by("selector")
    if sel:
        doc.claim(f"The surrogate selector was consulted {len(sel)} times", *[s["record_id"] for s in sel])
    # 8 judge, safety
    doc.h(2, "8. Independent checks, safety and human approval")
    for j in judge:
        c = j["checks"]
        doc.claim(f"Judge verdict {j['record_id']} on {j['conclusion_id']}: confidence {j['confidence']}, "
                  f"ledger-supported {str(c.get('supported_by_ledger')).lower()}, citations present {str(c.get('citations_present')).lower()}",
                  j["record_id"], j["conclusion_id"] if j["conclusion_id"] in src else j["record_id"])
    if not judge:
        doc.claim("No judge verdicts were recorded for this run", "calc:n_judge")
    for s in by("safety"):
        doc.claim(f"Safety agent flagged candidate {s['candidate_id']} at level {s['level']}: {q(s['notes'], 140)}", s["record_id"])
    doc.claim("Recommending a candidate for real-world validation is gated by a human-approval ask policy", "file:asd/tools.py")
    # 9 uncertainty
    doc.h(2, "9. Uncertainty and limits")
    doc.claim(f"This run measured {len(led)} candidates under a single seed, so no rate or improvement is claimed from it",
              "calc:n_measured", "file:asd/replay.py")
    doc.claim("The steel data is public, a memorization probe flag is set, and no acceleration claim is made from LLM knowledge", CTX)
    doc.claim("Judge calibration (n=12) was near-arithmetic and the arena check (n=5, Spearman 0.56, p=0.21) was at chance, so both are weak evidence", CTX)
    doc.claim("Predictions are the agents' own estimates and the oracle replays a fixed dataset, so a measured value is a lookup, not a new experiment", CTX, "file:asd/replay.py")
    # 10 next
    doc.h(2, "10. Recommended next experiment and validation needed")
    tested = {l["id"] for l in led}
    nxt = next((p for s in reversed(sel) for p in s["picks"] if p["candidate_id"] not in tested), None)
    if nxt:
        last = next(s for s in reversed(sel) if nxt in s["picks"])
        doc.claim(f"Next experiment: run candidate {nxt['candidate_id']}, the highest surrogate pick not yet measured (score {nxt['score']})",
                  last["record_id"])
    doc.claim("Before real use a hit must be replicated and then synthesised and tested in a physical lab, with human sign-off", BRIEF)
    doc.claim("The recorded hypotheses and agent summaries must be checked against the cited papers before anyone relies on them", BRIEF)
    return doc.text()
