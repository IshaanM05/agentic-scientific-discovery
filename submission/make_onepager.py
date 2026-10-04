"""Build the 1-page PDF report:  python submission/make_onepager.py [TeamName]

Edit the CONTENT dict below and re-run. Output: submission/<TeamName>_OnePager.pdf
"""
import sys
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Line, Polygon, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

TEAM = sys.argv[1] if len(sys.argv) > 1 else "HousePhD"
OUT = Path(__file__).with_name(f"{TEAM}_OnePager.pdf")

INK = colors.HexColor("#172033")
MUTED = colors.HexColor("#5a6478")
ACCENT = colors.HexColor("#2f5bd3")
LINE = colors.HexColor("#d9dee8")

CONTENT = {
    "title": "Princeton-Plainsboro: an agentic lab for exoplanet candidate diagnosis",
    "subtitle": "Hack-Nation Global AI Hackathon · Challenge 03: Agentic Scientific Discovery · "
                "Team " + TEAM,
    "challenge": [
        "Telescopes flag thousands of transit-like dips; most are eclipsing binaries, starspots, blends or "
        "glitches. The bottleneck is choosing <b>which vetting test to run next and when to stop</b>.",
        "<b>User:</b> exoplanet survey scientists and vetting teams who face more candidates than people.",
    ],
    "tools": [
        "<b>Gemini (flash) or Claude Sonnet</b>: Cameron reads live papers and writes cited briefs; optional agent voices.",
        "<b>arXiv + OpenAlex APIs</b>: live literature search; every citation is resolved before use.",
        "<b>Omnigent</b>: agent bundle (House root + 5 sub-agents), tools, guardrail policies.",
        "<b>NumPy / SciPy</b>: 8 light-curve tests; Bayesian posterior; expected information gain (EIG).",
        "<b>Streamlit</b>: live demo UI with human approval gates. "
        "<b>NASA Exoplanet Archive + MAST (lightkurve)</b>: 48 real Kepler candidates.",
    ],
    "worked": [
        "<b>1.9× lower test cost</b> than a fixed checklist at matched accuracy (240 blind synthetic targets, 90% CI 1.47–2.39).",
        "Accuracy 0.917 vs 0.846 (checklist); Brier 0.133 vs 0.243; human escalations 42% → 26%.",
        "Leak-proof evaluation: labels held only by a Data Gatekeeper, <b>0 agent label reads</b> in the audit.",
        "Live research guardrail: LLM citations outside the retrieved set are stripped automatically.",
    ],
    "challenging": [
        "<b>Synthetic → real transfer.</b> On real Kepler data accuracy fell to 0.38–0.54. Leave-one-out "
        "recalibration cut confident errors from 11 to 2; we report this as a negative result.",
        "<b>Correlated tests.</b> Tests share one fit, so posteriors were overconfident; added CV-fitted tempering.",
        "<b>LLM reliability.</b> Invented citations and leaked drafting text; fixed with JSON output plus an ID allow-list.",
        "<b>Free-tier quotas.</b> Gemini models hit daily limits; added automatic fallback across models.",
    ],
    "time": [
        "Problem framing, hypothesis space H1–H5, agent roles and policy design",
        "Synthetic light-curve generator and the 8 vetting tests",
        "Likelihood calibration, EIG planner, agent loop, whiteboard and ledger",
        "Benchmark (baselines, ablations, oracle), real-Kepler transfer test",
        "Omnigent bundle + live run, Streamlit UI, live LLM research, submission",
    ],
    "next": "If we had 24 more hours, we'd calibrate on ~2,000 real DR25 Kepler candidates, learn a joint "
            "likelihood instead of assuming independent tests, and re-measure the speedup on real and TESS data.",
}


def styles():
    base = dict(fontName="Helvetica", fontSize=8.4, leading=10.6, textColor=INK, alignment=TA_LEFT)
    return {
        "title": ParagraphStyle("t", **{**base, "fontName": "Helvetica-Bold", "fontSize": 14.5, "leading": 17}),
        "sub": ParagraphStyle("s", **{**base, "fontSize": 8, "textColor": MUTED}),
        "h": ParagraphStyle("h", **{**base, "fontName": "Helvetica-Bold", "fontSize": 9.6, "leading": 12,
                                    "textColor": ACCENT, "spaceBefore": 5, "spaceAfter": 2}),
        "b": ParagraphStyle("b", **{**base, "leftIndent": 8, "bulletIndent": 0}),
        "p": ParagraphStyle("p", **base),
    }


def diagram(width):
    d = Drawing(width, 46)
    boxes = ["Gatekeeper\n(anonymize)", "House\n(differential)", "Cameron\n(live research)", "Cuddy\n(EIG / cost)",
             "Chase\n(8 tests)", "Foreman\n(skeptic)", "Posterior\nupdate", "Verdict\n+ human gate"]
    n = len(boxes)
    gap = 7
    bw = (width - gap * (n - 1)) / n
    for i, label in enumerate(boxes):
        x = i * (bw + gap)
        d.add(Rect(x, 10, bw, 28, rx=3, ry=3, fillColor=colors.HexColor("#eef2fb"), strokeColor=ACCENT,
                   strokeWidth=0.6))
        for j, part in enumerate(label.split("\n")):
            d.add(String(x + bw / 2, 27 - j * 9, part, fontName="Helvetica-Bold" if j == 0 else "Helvetica",
                         fontSize=6.6 if j == 0 else 5.8, fillColor=INK, textAnchor="middle"))
        if i < n - 1:
            x2 = x + bw
            d.add(Line(x2 + 0.5, 24, x2 + gap - 1.5, 24, strokeColor=MUTED, strokeWidth=0.6))
            d.add(Polygon([x2 + gap - 1.5, 24, x2 + gap - 3.5, 25.3, x2 + gap - 3.5, 22.7], fillColor=MUTED,
                          strokeColor=MUTED))
    # loop-back arrow from posterior to Cuddy
    xa = 6 * (bw + gap) + bw / 2
    xb = 3 * (bw + gap) + bw / 2
    for seg in ((xa, 10, xa, 3), (xa, 3, xb, 3), (xb, 3, xb, 9)):
        d.add(Line(*seg, strokeColor=ACCENT, strokeWidth=0.6))
    d.add(Polygon([xb, 10, xb - 1.3, 8, xb + 1.3, 8], fillColor=ACCENT, strokeColor=ACCENT))
    d.add(String((xa + xb) / 2, 4.5, "re-plan after every result until the stopping rule fires", fontSize=5.6,
                 fillColor=ACCENT, textAnchor="middle", fontName="Helvetica-Oblique"))
    return d


def build():
    st = styles()
    doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=11 * mm,
                            bottomMargin=10 * mm, title=CONTENT["title"], author=f"Team {TEAM}")
    W = doc.width
    bullets = lambda items: [Paragraph(x, st["b"], bulletText="•") for x in items]  # noqa: E731
    story = [Paragraph(CONTENT["title"], st["title"]), Spacer(1, 2), Paragraph(CONTENT["subtitle"], st["sub"]),
             Spacer(1, 5), diagram(W), Spacer(1, 2)]

    def section(head, items, numbered=False):
        out = [Paragraph(head, st["h"])]
        if numbered:
            out += [Paragraph(x, st["b"], bulletText=f"{i + 1}.") for i, x in enumerate(items)]
        else:
            out += bullets(items)
        return out

    left = (section("Challenge tackled", CONTENT["challenge"]) + section("Tools / ML models used", CONTENT["tools"])
            + section("How we spent our time (in order)", CONTENT["time"], numbered=True))
    right = (section("What worked well", CONTENT["worked"]) + section("What was challenging", CONTENT["challenging"]))
    cols = Table([[left, right]], colWidths=[W * 0.5 - 4, W * 0.5 - 4], hAlign="LEFT")
    cols.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                              ("RIGHTPADDING", (0, 0), (0, 0), 8), ("RIGHTPADDING", (1, 0), (1, 0), 0),
                              ("LINEAFTER", (0, 0), (0, 0), 0.4, LINE)]))
    story.append(cols)

    res = Table([["Condition (240 blind targets)", "Accuracy @0.9", "Mean cost", "Brier", "To human"],
                 ["Fixed checklist", "0.846", "6.62", "0.243", "42%"],
                 ["Planner only (no debate)", "0.883", "5.56", "0.159", "24%"],
                 ["Full House team", "0.917", "6.62", "0.133", "26%"],
                 ["Real Kepler (48 KOIs, transfer)", "0.38–0.54", "—", "—", "96% after recal."]],
                colWidths=[W * 0.36, W * 0.16, W * 0.14, W * 0.12, W * 0.22])
    res.setStyle(TableStyle([("FONT", (0, 0), (-1, -1), "Helvetica", 7.8), ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.6),
                             ("TEXTCOLOR", (0, 0), (-1, 0), MUTED), ("FONT", (0, 3), (-1, 3), "Helvetica-Bold", 7.8),
                             ("BACKGROUND", (0, 3), (-1, 3), colors.HexColor("#eef2fb")),
                             ("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE), ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                             ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6)]))
    story += [Paragraph("Results", st["h"]), res, Spacer(1, 5), Paragraph("<b>Next:</b> " + CONTENT["next"], st["p"]),
              Spacer(1, 3), Paragraph("Data &amp; references: NASA Exoplanet Archive KOI cumulative table; MAST Kepler "
                                      "light curves; method papers resolved on arXiv (Coughlin+2016, Thompson+2018, "
                                      "Seager &amp; Mallén-Ornelas 2003, Bryson+2013, McQuillan+2014).", st["sub"])]
    doc.build(story)
    from reportlab.lib.utils import ImageReader  # noqa: F401  (keeps reportlab import check honest)
    print(OUT)


if __name__ == "__main__":
    build()
