"""Traceable report: generation, the source checker (including deliberately failing reports), the polish hook,
and the no-hidden-truth guard. Offline, no model."""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from asd import report as R

ROOT = Path(__file__).resolve().parent.parent
STEEL_DIR, LL_DIR = "runs/t011", "runs/ll-offline-w3100"


def _script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


mk, chk = _script("make_report"), _script("check_report")


@pytest.fixture(scope="module")
def steel():
    return mk.build("steel", STEEL_DIR), R.load_sources("steel", STEEL_DIR)


@pytest.fixture(scope="module")
def ll():
    return mk.build("labloop", LL_DIR), R.load_sources("labloop", LL_DIR)


def problems(md, src):
    return R.check_markdown(md, src)


# ---------------------------------------------------------------- generation
def test_steel_report_passes_and_has_required_sections(steel):
    md, src = steel
    assert problems(md, src) == []
    for sec in ("1. Question", "2. Evidence", "3. Hypotheses", "4. Experiments", "5. Experiment choices",
                "6. Negative results", "7. What changed", "9. Uncertainty", "10. Recommended next experiment"):
        assert sec in md
    assert "agent-generated" in md and "ledger-0001" in md and "rec-0014" in md and "1309.1" in md
    assert "validation" in md.lower() and "physical lab" in md


def test_every_steel_hypothesis_is_labelled_with_kill_condition_and_status(steel):
    md, _ = steel
    for hid in ("H1", "H2", "H3"):
        assert f"**{hid}** carries the label" in md and f"Kill condition for {hid}" in md and f"Final status of {hid}" in md


def test_labloop_report_passes_and_labels_every_hypothesis(ll):
    md, src = ll
    assert problems(md, src) == []
    rows = [l for l in md.splitlines() if l.startswith("| H")]
    assert len(rows) >= 6 and all("agent-generated" in r for r in rows)
    assert "offline rule-based run" in md and "not evidence about real devices" in md
    assert md.count("| E0") >= 40  # every film has its own row with a notebook id and measured values


def test_committed_reports_are_fresh_and_pass_checker():
    for kind, rd, out in (("steel", STEEL_DIR, "docs/REPORT_STEEL.md"), ("labloop", LL_DIR, "docs/REPORT_LABLOOP.md")):
        committed = (ROOT / out).read_text(encoding="utf-8")
        assert committed == mk.build(kind, rd), f"{out} is stale: rerun python scripts/make_report.py all"
        assert chk.check_file(ROOT / out) == []


def test_fresh_labloop_run_through_tools_reports(tmp_path):
    """End to end on a small budget: simulate through the tool layer, report, check."""
    out = mk.simulate(3101, 1, 6.0, tmp_path / "ll-mini")
    md = mk.build("labloop", out)
    assert problems(md, R.load_sources("labloop", out)) == []
    # the manifest uses the path given; rebuild from an absolute dir works too
    assert (out / "notebook.sqlite").exists() and "| E001 |" in md


def test_generation_is_deterministic(steel):
    assert mk.build("steel", STEEL_DIR) == steel[0]


# ---------------------------------------------------------------- the checker fails what it should
def test_deliberately_failing_case_through_the_cli(tmp_path):
    good = (ROOT / "docs/REPORT_STEEL.md").read_text(encoding="utf-8")
    bad = good.replace("[src: rec-0014]", "", 1).replace("[src: ledger-0002, rec-0019]", "[src: rec-9999]", 1)
    assert bad != good
    p = tmp_path / "bad.md"
    p.write_text(bad, encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "scripts/check_report.py"), str(p)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 1 and "FAIL" in r.stdout
    assert "unknown source id: rec-9999" in r.stdout
    ok = subprocess.run([sys.executable, str(ROOT / "scripts/check_report.py"), str(ROOT / "docs/REPORT_STEEL.md")],
                        capture_output=True, text=True, cwd=ROOT)
    assert ok.returncode == 0 and "OK" in ok.stdout


def test_claim_without_source_id_fails(steel):
    md, src = steel
    bad = md + "\nThe steel reaches 2500 MPa.\n"
    assert any(p == "no source id" for _, p, _ in problems(bad, src))


def test_unknown_source_id_fails(steel):
    md, src = steel
    bad = md + "\n- A claim about a run [src: rec-4242]\n"
    assert any("unknown source id: rec-4242" in p for _, p, _ in problems(bad, src))


def test_fabricated_number_fails(steel):
    md, src = steel
    bad = md + "\n- Candidate c000 measured 1999.9 MPa [src: ledger-0001]\n"
    assert any("number 1999.9 not found" in p for _, p, _ in problems(bad, src))
    good = md + "\n- Candidate c000 measured 1309.1 MPa [src: ledger-0001]\n"
    assert problems(good, src) == []


def test_altered_quote_fails(steel):
    md, src = steel
    bad = md + "\n- The agent summary says “Co-free maraging steel achieves 3000 MPa yield strength.” [src: rec-0008]\n"
    assert any("quote not verbatim" in p for _, p, _ in problems(bad, src))


def test_two_sentences_under_one_tag_fail(steel):
    md, src = steel
    bad = md + "\n- Candidate c000 was run. It was a hit [src: ledger-0001]\n"
    assert any("more than one sentence" in p for _, p, _ in problems(bad, src))


def test_text_after_last_tag_fails(steel):
    md, src = steel
    bad = md + "\n- Candidate c000 was run [src: ledger-0001] and it was great\n"
    assert any("after the last source tag" in p for _, p, _ in problems(bad, src))


def test_labloop_checker_catches_tampered_measurement(ll):
    md, src = ll
    row = next(l for l in md.splitlines() if l.startswith("| E001 |"))
    cells = row.split(" | ")
    bad = md.replace(row, row.replace(cells[3], "1.111"), 1)
    assert any("not found in cited sources" in p for _, p, _ in problems(bad, src))


def test_hidden_truth_terms_fail_and_never_appear(steel, ll):
    md, src = ll
    assert any("hidden-truth term" in p for _, p, _ in problems(md + "\n- The eg_true of E001 was 1.3 [src: nb:E001]\n", src))
    for text in (steel[0], ll[0]):
        assert not any(t in text.lower() for t in R.FORBIDDEN)


def test_loader_refuses_run_dir_with_hidden_truth(tmp_path):
    d = tmp_path / "leaky"
    shutil.copytree(ROOT / STEEL_DIR, d)
    lines = (d / "record.jsonl").read_text().splitlines()
    e = json.loads(lines[0])
    e["true_hits"] = ["c001"]
    lines[0] = json.dumps(e)
    (d / "record.jsonl").write_text("\n".join(lines) + "\n")
    with pytest.raises(R.ReportError, match="hidden-truth"):
        R.load_steel(d)


def test_ledger_record_disagreement_is_reported_not_hidden(tmp_path):
    d = tmp_path / "t011x"
    shutil.copytree(ROOT / STEEL_DIR, d)
    led = [json.loads(l) for l in (d / "ledger.jsonl").read_text().splitlines()]
    led[0]["value"] = 1500.0
    (d / "ledger.jsonl").write_text("\n".join(json.dumps(x) for x in led) + "\n")
    md = R.render_steel(d)
    assert "Integrity warning: ledger entry ledger-0001 and record rec-0014 disagree" in md


# ---------------------------------------------------------------- polish hook: wording only, never facts
def test_polish_accepts_rewording_and_rejects_new_facts(steel):
    md, src = steel
    reword = lambda t: t.replace("This run used", "The run used")
    out = R.polish(md, reword, src)
    assert "The run used seed 21" in out and problems(out, src) == []
    add_fact = lambda t: t + " and reached 9999 MPa"
    assert R.polish(md, add_fact, src) == md
    drop_quote = lambda t: t.replace("“", "").replace("”", "")
    assert R.polish(md, drop_quote, src) == md
    junk = lambda t: None
    assert R.polish(md, junk, src) == md


def test_make_report_polish_flag_keeps_check_green(tmp_path, monkeypatch):
    mod = tmp_path / "fakepolish.py"
    mod.write_text("def rewrite(t):\n    return t.replace('Which steel compositions', 'Which steels')\n")
    monkeypatch.syspath_prepend(str(tmp_path))
    md = mk.build("steel", STEEL_DIR, "fakepolish:rewrite")
    assert "Which steels in a 312-candidate" in md and problems(md, R.load_sources("steel", STEEL_DIR)) == []


def test_missing_manifest_and_unknown_kind(tmp_path):
    p = tmp_path / "x.md"
    p.write_text("- a claim [src: rec-0001]\n")
    assert "no asd-report manifest" in chk.check_file(p)[0]
    with pytest.raises(R.ReportError):
        R.load_sources("nope", ".")
