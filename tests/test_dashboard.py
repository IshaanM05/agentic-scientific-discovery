import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "dashboard"))
import data as D  # noqa: E402


def test_parse_every_run():
    n = D.parse_all()
    assert n["t011"] > 0 and "judge:t011" in n
    assert len(D.load_arena()["hypotheses"]) == 5
    assert D.load_policies()["deny"]
    assert D.readme_section("Judge")
    assert D.load_results()["headline"].exists()
