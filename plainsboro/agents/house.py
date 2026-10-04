"""House, lead diagnostician / insight agent (design 5.1).

Owns: bold, non-obvious hypotheses and the final verdict. "Everybody lies":
House reads the raw signal for clues the default differential misses, always
puts a contrarian hypothesis on the table, and asks Cuddy for the test that
would settle it. House cannot override the posterior; the verdict must equal
the posterior's top class (an override would need human approval).
"""
from __future__ import annotations

import numpy as np

from ..config import HYP_IDS, HYP_LABELS, HYPOTHESES
from ..planner.posterior import pairwise_info
from ..schemas import Dissent, HypothesisProposal, PredictedSignature, Verdict
from ..vetting.registry import REGISTRY

FOLLOWUP = {
    "H1": ["high-resolution imaging to exclude unresolved companions",
           "radial-velocity mass measurement",
           "statistical validation (false-positive probability) before any 'validated planet' claim"],
    "H2": ["spectroscopic radial velocities to confirm a stellar-mass companion"],
    "H3": ["high-resolution imaging / difference-image centroid analysis to locate the contaminating star"],
    "H4": ["longer-baseline photometry to follow spot evolution", "check for rotation in other quarters"],
    "H5": ["inspect neighbouring stars on the same CCD channel for the same dips",
           "re-reduce with alternative systematics correction"],
}


class House:
    name = "house"

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    # ---- intake: read the signal for clues -------------------------------------------
    def differential(self, target) -> list[HypothesisProposal]:
        """Agent-generated hypotheses from signal features. Labeled origin=agent_generated."""
        s, st, lc = target.signal, target.stellar, target.lc
        P, dur_d, depth = s["period_d"], s["duration_h"] / 24, s["depth_ppm"] * 1e-6
        props = [HypothesisProposal(
            id="H2-2P", name="EB at twice the reported period", parent="H2",
            mechanism="Pipelines fold twin-star eclipses at half the true period; primary and secondary "
                      "then alternate as 'odd' and 'even' transits.",
            predicted_signatures=[PredictedSignature(test_id="T-odd-even", expected_outcome=">3 sigma")])]
        if depth > 0.03:
            props.append(HypothesisProposal(
                id="H2-deep", name="Stellar-size companion", parent="H2",
                mechanism=f"Depth {depth * 100:.1f}% implies Rp/R* ~ {np.sqrt(depth):.2f}; too big for most planets.",
                predicted_signatures=[PredictedSignature(test_id="T-secondary", expected_outcome=">4 sigma"),
                                      PredictedSignature(test_id="T-shape", expected_outcome="V-shaped")]))
        a_r = 4.206 * st["rho_cat"] ** (1 / 3) * P ** (2 / 3)
        t_exp = P / (np.pi * a_r)
        ratio = dur_d / t_exp
        if ratio > 1.6:
            props.append(HypothesisProposal(
                id="H3-long", name="Blend: dips too long for this star", parent="H3",
                mechanism=f"Duration is {ratio:.1f}x the central-transit duration expected for the catalog "
                          "star; the eclipsing body may orbit a different (background) star.",
                predicted_signatures=[PredictedSignature(test_id="T-centroid", expected_outcome=">5 sigma"),
                                      PredictedSignature(test_id="T-density", expected_outcome="much lower")]))
        flagged = lc.time[lc.quality]
        if len(flagged) > 3:
            spacing = float(np.median(np.diff(flagged)))
            for h in (1, 2):
                if abs(P / (h * spacing) - 1) < 0.03:
                    props.append(HypothesisProposal(
                        id="H5-dump", name="Momentum-dump artifact", parent="H5",
                        mechanism=f"Signal period {P:.3f} d matches {h}x the spacing of flagged cadences "
                                  f"({spacing:.3f} d): the spacecraft is lying, not the star.",
                        predicted_signatures=[PredictedSignature(test_id="T-systematics",
                                                                 expected_outcome=">50% flagged")]))
                    break
        if dur_d > 0.1 * P:
            props.append(HypothesisProposal(
                id="H4-rot", name="Rotational modulation", parent="H4",
                mechanism=f"Dips last {dur_d / P * 100:.0f}% of the period; spots, not an occultor.",
                predicted_signatures=[PredictedSignature(test_id="T-periodogram",
                                                         expected_outcome="matches signal period")]))
        return props

    # ---- each round: challenge the leader -----------------------------------------------
    def contrarian(self, wb, proposals: list[HypothesisProposal], tables) -> dict:
        post = wb.post_array()
        lead = int(np.argmax(post))
        order = np.argsort(-post)
        contra = int(order[1])
        tested = wb.tested()
        # prefer the parent of a still-plausible agent-generated proposal whose predicted test is untested
        chosen_prop = None
        for p in proposals:
            j = HYP_IDS.index(p.parent)
            if j != lead and post[j] >= 0.05 and any(ps.test_id not in tested for ps in p.predicted_signatures):
                contra, chosen_prop = j, p
                break
        best_test, best_bits = None, -1.0
        for tid in REGISTRY:
            if tid in tested:
                continue
            bits = pairwise_info(post, tables.table(tid), lead, contra, tables.temper)
            if bits > best_bits:
                best_test, best_bits = tid, bits
        if chosen_prop:
            for ps in chosen_prop.predicted_signatures:
                if ps.test_id not in tested:
                    best_test = ps.test_id
                    break
        text = (f"Everyone thinks it's {HYP_LABELS[HYP_IDS[lead]]} ({post[lead]:.0%}). "
                f"What if it's {HYP_LABELS[HYP_IDS[contra]]} ({post[contra]:.0%})?")
        if chosen_prop:
            text += f" My hypothesis {chosen_prop.id} [agent-generated]: {chosen_prop.mechanism}"
        if best_test:
            text += f" Run {best_test}; it separates the two best."
        return {"leader": HYP_IDS[lead], "contrarian": HYP_IDS[contra], "request": best_test,
                "proposal": chosen_prop.id if chosen_prop else None, "text": text}

    def reopen(self, old: str, new: str, post) -> str:
        return (f"REOPEN: the leader flipped from {HYP_LABELS[old]} to {HYP_LABELS[new]} "
                f"({max(post.values()):.0%}). The earlier assumption was wrong. What does the new leader predict "
                "that we have not tested?")

    # ---- verdict -----------------------------------------------------------------------------
    def verdict(self, wb, interval, threshold: float, run_ids, evidence_ids, critiques) -> Verdict:
        post = wb.posterior
        label = max(post, key=post.get)
        top = post[label]
        if label == "H1":
            text, strength = "planet candidate (vetting recommendation, not a confirmation)", "candidate"
        else:
            text, strength = f"likely false positive: {HYPOTHESES[label].replace('_', ' ')}", "likely_false_positive"
        if top < 0.6:
            strength = "undetermined"
            text = f"undetermined; leaning {text}"
        dissent = [Dissent(agent="foreman", objection=c["text"]) for c in critiques]
        ranked = sorted(post.items(), key=lambda kv: -kv[1])
        if len(ranked) > 1 and ranked[1][1] >= 0.05:
            dissent.append(Dissent(agent="house", objection=f"Cannot exclude {HYP_LABELS[ranked[1][0]]} "
                                                             f"(posterior {ranked[1][1]:.2f})."))
        needs_human = top < threshold or bool(critiques)
        return Verdict(target_id=wb.target_id, label=label, label_text=text, posterior=post,
                       top_posterior=round(top, 4), interval=interval, evidence_ids=evidence_ids,
                       run_ids=run_ids, dissent=dissent, required_followup=FOLLOWUP[label],
                       needs_human=needs_human, claim_strength=strength,
                       tests_used=wb.budget["used"], cost_used=round(wb.budget["cost_units_used"], 2))
