"""Custom Omnigent policies (function policies: event dict -> {"result": ALLOW|DENY|ASK}).

experiment_budget : DENY run_experiment after `limit` calls in the session (cost gate).
human_approval    : ASK (park for human approval) before recommend_for_validation (always) and before
                    run_experiment once `ask_after` experiments are spent.
safety_gate       : DENY (hard) propose_processing_route / recommend_for_validation whose arguments name a
                    flagged-hazard processing route (e.g. unshielded hydrogen charging, molten-salt quench).
Budget/approval are factories (handler + factory_params in agent YAML); safety_gate is a plain evaluator.
"""
_ALLOW = {"result": "ALLOW"}
_KEY = "_asd_experiments"


def _count(event):
    return int((event.get("session_state") or {}).get(_KEY, 0))


def experiment_budget(limit: int = 60):
    def evaluate(event):
        if event.get("type") != "tool_call" or event.get("target") != "run_experiment":
            return _ALLOW
        n = _count(event)
        if n >= limit:
            return {"result": "DENY", "reason": f"experiment budget {limit} exhausted"}
        return {"result": "ALLOW",
                "state_updates": [{"key": _KEY, "action": "set", "value": n + 1}]}
    return evaluate


def human_approval(ask_after: int = 30):
    def evaluate(event):
        if event.get("type") != "tool_call":
            return _ALLOW
        tool = event.get("target")
        if tool == "recommend_for_validation":
            return {"result": "ASK", "reason": "Real-world validation recommendation needs human approval"}
        if tool == "run_experiment" and _count(event) >= ask_after:
            return {"result": "ASK", "reason": f"More than {ask_after} experiments spent; approve continuing"}
        return _ALLOW
    return evaluate


HAZARD_TERMS = ("unshielded", "no ventilation", "hydrogen charging", "molten salt", "cyanide", "hf acid",
                "without ppe", "bypass interlock", "open flame", "asbestos")


def safety_gate(event):
    """Hard gate (plain evaluator, no factory): DENY any hazardous-route request. Matches case-insensitively
    on the JSON of the call arguments. Not advisory: the tool never runs."""
    if event.get("type") != "tool_call" or event.get("target") not in (
            "propose_processing_route", "recommend_for_validation"):
        return _ALLOW
    import json
    blob = json.dumps((event.get("data") or {}).get("arguments") or {}, default=str).lower()
    hit = [t for t in HAZARD_TERMS if t in blob]
    if hit:
        return {"result": "DENY", "reason": f"safety gate: flagged hazard {hit[0]!r} in requested route"}
    return _ALLOW
