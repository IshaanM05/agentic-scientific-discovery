"""Lab policies, written as Omnigent policy handlers (design 8.1).

Each handler follows Omnigent's policy contract:

    def handler(event: PolicyEvent) -> PolicyResponse | None

where `event` has keys type / target / data{name, arguments} / context{actor} /
session_state, and the response is {"result": "ALLOW"|"DENY"|"ASK", "reason": ...,
"state_updates": [...]}, or None to abstain. Parameterized policies are
factories (Omnigent `factory_params`).

The same functions are referenced from configs/agents/*.yaml (Omnigent runtime)
and evaluated by `PolicyEngine` in the local runtime, so the boundary is
identical in both paths.
"""
from __future__ import annotations

from typing import Callable

from .literature import TARGET_NAME_PATTERN
from .vetting.registry import REGISTRY

PolicyEvent = dict
PolicyResponse = dict

TEST_TOOLS = {"run_vetting_test", "rerun_vetting_test"}


def _is_tool_call(event, names=None) -> bool:
    if event.get("type") != "tool_call":
        return False
    return names is None or event.get("target") in names


def _args(event) -> dict:
    return (event.get("data") or {}).get("arguments") or {}


def _actor(event) -> str:
    """Agent name in the local runtime. Under Omnigent, context.actor is the human identity
    ({run_as, client_id}); per-agent tool scoping is then enforced by each agent's own tool list."""
    a = (event.get("context") or {}).get("actor")
    if isinstance(a, dict) or a is None:
        return "omnigent"
    return str(a).lower()


# --- budget_cap ---------------------------------------------------------------

def budget_cap(max_tests: int = 5, cost_units_max: float = 10.0) -> Callable:
    """No more than max_tests tests / cost_units_max per target. Exceeding asks a human."""

    def evaluate(event: PolicyEvent) -> PolicyResponse | None:
        if not _is_tool_call(event, TEST_TOOLS):
            return None
        a = _args(event)
        tid, test_id = a.get("target_id"), a.get("test_id")
        if test_id not in REGISTRY:
            return None  # test_allowlist handles it
        st = event.get("session_state") or {}
        used = st.get(f"budget:{tid}:tests", 0)
        cost = st.get(f"budget:{tid}:cost", 0.0)
        rerun = event.get("target") == "rerun_vetting_test"
        add_cost = float(a.get("cost_units", REGISTRY[test_id].cost))
        add_tests = 0 if rerun else 1
        updates = [{"action": "increment", "key": f"budget:{tid}:tests", "value": add_tests},
                   {"action": "increment", "key": f"budget:{tid}:cost", "value": add_cost}]
        if used + add_tests > max_tests or cost + add_cost > cost_units_max + 1e-9:
            # state_updates are applied only if the human approves the extension
            return {"result": "ASK",
                    "reason": f"budget_cap: {test_id} would use {used + add_tests}/{max_tests} tests and "
                              f"{cost + add_cost:.1f}/{cost_units_max:.1f} cost units for {tid}; "
                              "a human must approve a budget extension.",
                    "state_updates": updates}
        return {"result": "ALLOW", "state_updates": updates}

    return evaluate


# --- test_allowlist -------------------------------------------------------------

def test_allowlist(event: PolicyEvent) -> PolicyResponse | None:
    """Chase may only run tests in the registry, and only Chase may run them."""
    if not _is_tool_call(event, TEST_TOOLS):
        return None
    test_id = _args(event).get("test_id")
    if test_id not in REGISTRY:
        return {"result": "DENY", "reason": f"test_allowlist: '{test_id}' is not in the approved registry."}
    if _actor(event) not in ("chase", "chase-worker", "omnigent"):
        return {"result": "DENY", "reason": f"test_allowlist: only Chase executes tests (actor={_actor(event)})."}
    return {"result": "ALLOW"}


# --- no_label_access ----------------------------------------------------------------

LABEL_TOKENS = ("disposition", "koi_pdisposition", "koi_disposition", "fpflag", "koi_fpflag", "ground_truth",
                "truth_label")


def no_label_access(event: PolicyEvent) -> PolicyResponse | None:
    """Only the Data Gatekeeper / evaluator may touch ground-truth labels."""
    if event.get("type") != "tool_call":
        return None
    name = (event.get("target") or "").lower()
    blob = (name + " " + str(_args(event))).lower()
    if any(tok in blob for tok in LABEL_TOKENS) or name.startswith("gatekeeper_"):
        if _actor(event) not in ("gatekeeper", "evaluator"):
            return {"result": "DENY", "reason": f"no_label_access: {_actor(event)} attempted label access via {name}."}
    return None


# --- no_target_specific_lookup ---------------------------------------------------------

def no_target_specific_lookup(benchmark_mode: bool = True) -> Callable:
    """In benchmark mode Cameron may not search literature for the specific target."""

    def evaluate(event: PolicyEvent) -> PolicyResponse | None:
        if not _is_tool_call(event, {"literature_search"}):
            return None
        if not benchmark_mode:
            return {"result": "ALLOW", "reason": "demo mode: target-specific lookup permitted (labeled)."}
        a = _args(event)
        q = str(a.get("query", ""))
        tid = str(a.get("target_id", "")).strip()
        if TARGET_NAME_PATTERN.search(q) or (tid and tid.lower() in q.lower()):
            return {"result": "DENY",
                    "reason": "no_target_specific_lookup: query names the target (label-leak risk)."}
        return {"result": "ALLOW"}

    return evaluate


# --- no_external_writes ------------------------------------------------------------------

EXTERNAL_WRITE_TOOLS = {"post_to_archive", "submit_to_catalog", "send_email", "http_post", "publish_result",
                        "request_telescope_time"}


def no_external_writes(event: PolicyEvent) -> PolicyResponse | None:
    if _is_tool_call(event, EXTERNAL_WRITE_TOOLS):
        return {"result": "DENY", "reason": "no_external_writes: the lab never writes to archives, catalogs or email."}
    return None


# --- human_approval_required -----------------------------------------------------------------

STRONG_CLAIM_WORDS = ("confirmed", "validated planet", "discovery of", "is a planet")


def human_approval_required(event: PolicyEvent) -> PolicyResponse | None:
    """Consequential actions route to a human: follow-up requests, posterior overrides, strong claims."""
    if event.get("type") != "tool_call":
        return None
    name = event.get("target")
    a = _args(event)
    if name == "propose_followup":
        return {"result": "ASK", "reason": f"Follow-up observation proposal ({a.get('kind', 'unspecified')}) "
                                           "needs scientist approval."}
    if name == "override_posterior":
        return {"result": "ASK", "reason": "House wants a verdict inconsistent with the posterior."}
    if name == "issue_verdict":
        text = str(a.get("label_text", "")).lower()
        if any(w in text for w in STRONG_CLAIM_WORDS):
            return {"result": "DENY",
                    "reason": "Claim stronger than 'candidate'/'likely false positive' is not allowed "
                              "without independent follow-up; rephrase."}
    return None


# --- provenance_required ----------------------------------------------------------------------

def provenance_required(event: PolicyEvent) -> PolicyResponse | None:
    if not _is_tool_call(event, {"issue_verdict"}):
        return None
    a = _args(event)
    if not a.get("run_ids") and not a.get("evidence_ids"):
        return {"result": "DENY", "reason": "provenance_required: verdict cites no run records or evidence."}
    return {"result": "ALLOW"}


# --- low_confidence_needs_human (cost_of_wrong_label_logged) -------------------------------------

def low_confidence_needs_human(threshold: float = 0.9) -> Callable:
    def evaluate(event: PolicyEvent) -> PolicyResponse | None:
        if not _is_tool_call(event, {"issue_verdict"}):
            return None
        a = _args(event)
        if "top_posterior" not in a:
            return None  # Omnigent path: the issue_verdict tool computes the posterior and sets needs_human itself
        if float(a["top_posterior"]) < threshold and not a.get("needs_human"):
            return {"result": "DENY", "reason": f"cost_of_wrong_label_logged: posterior < {threshold} must be "
                                                "flagged needs_human=true."}
        return None
    return evaluate


# --- engine -----------------------------------------------------------------------------------

def default_policies(cfg: dict, benchmark_mode: bool = True) -> dict[str, Callable]:
    return {
        "test_allowlist": test_allowlist,
        "no_label_access": no_label_access,
        "no_external_writes": no_external_writes,
        "no_target_specific_lookup": no_target_specific_lookup(benchmark_mode),
        "budget_cap": budget_cap(cfg["budget"]["max_tests"], cfg["budget"]["cost_units_max"]),
        "human_approval_required": human_approval_required,
        "provenance_required": provenance_required,
        "low_confidence_needs_human": low_confidence_needs_human(cfg["stopping"]["posterior_threshold"]),
    }


class PolicyEngine:
    """Local evaluator with Omnigent semantics: DENY beats ASK beats ALLOW; state_updates applied on ALLOW."""

    def __init__(self, policies: dict[str, Callable]):
        self.policies = policies
        self.session_state: dict = {}

    def evaluate(self, actor: str, tool: str, arguments: dict) -> dict:
        event = {"type": "tool_call", "target": tool, "data": {"name": tool, "arguments": arguments},
                 "context": {"actor": actor}, "session_state": dict(self.session_state), "request_data": None}
        decisions = []
        for name, fn in self.policies.items():
            r = fn(event)
            if r is not None:
                decisions.append((name, r))
        verdict = "ALLOW"
        reasons = []
        for name, r in decisions:
            if r["result"] == "DENY":
                verdict = "DENY"
                reasons.append(f"[{name}] {r.get('reason', '')}")
        if verdict != "DENY":
            for name, r in decisions:
                if r["result"] == "ASK":
                    verdict = "ASK"
                    reasons.append(f"[{name}] {r.get('reason', '')}")
        updates = [u for _, r in decisions for u in r.get("state_updates", []) or []]
        return {"result": verdict, "reasons": reasons, "evaluated": [n for n, _ in decisions],
                "state_updates": updates}

    def apply(self, updates: list[dict]):
        for u in updates:
            k, act = u["key"], u["action"]
            if act == "set":
                self.session_state[k] = u["value"]
            elif act == "increment":
                self.session_state[k] = self.session_state.get(k, 0) + u.get("value", 1)
            elif act == "delete":
                self.session_state.pop(k, None)
            elif act == "append":
                self.session_state.setdefault(k, []).append(u["value"])
