"""JSON schemas for every agent output in the loop."""
from jsonschema import validate

HYPOTHESIS = {
    "type": "object",
    "required": ["id", "text", "x_pred", "prediction"],
    "properties": {
        "id": {"type": "string"},
        "text": {"type": "string"},
        "x_pred": {"type": "number", "minimum": 0, "maximum": 1},
        "prediction": {"type": "number"},
    },
    "additionalProperties": False,
}
HYPOTHESES = {"type": "array", "minItems": 1, "items": HYPOTHESIS}
PICK = {
    "type": "object",
    "required": ["hypothesis_id", "x", "rationale"],
    "properties": {"hypothesis_id": {"type": "string"}, "x": {"type": "number"},
                   "rationale": {"type": "string"}},
    "additionalProperties": False,
}
RESULT = {
    "type": "object",
    "required": ["x", "y", "cost"],
    "properties": {"x": {"type": "number"}, "y": {"type": "number"}, "cost": {"type": "integer"}},
    "additionalProperties": False,
}
ANALYSIS = {
    "type": "object",
    "required": ["hypothesis_id", "error", "supported"],
    "properties": {"hypothesis_id": {"type": "string"}, "error": {"type": "number"},
                   "supported": {"type": "boolean"}},
    "additionalProperties": False,
}
DECISION = {
    "type": "object",
    "required": ["action", "reason"],
    "properties": {"action": {"enum": ["explore", "exploit", "replicate", "stop"]},
                   "reason": {"type": "string"}},
    "additionalProperties": False,
}


def check(obj, schema):
    validate(obj, schema)
    return obj


def _obj(req, props):
    return {"type": "object", "required": req, "properties": props}


_STR, _NUM = {"type": "string"}, {"type": "number"}
LIT_OUT = _obj(["citations", "record_id"], {"citations": {"type": "array"}, "record_id": _STR})
HYP_REC = _obj(["id", "text", "candidate_ids", "predicted_value", "assumption", "citations", "label"], {
    "id": _STR, "text": {"type": "string", "minLength": 5},
    "candidate_ids": {"type": "array", "items": _STR, "minItems": 1},
    "predicted_value": {"type": "number", "minimum": 0, "maximum": 5000},
    "assumption": {"type": "string", "minLength": 3},
    "citations": {"type": "array", "minItems": 1, "items": _STR},
    "label": {"const": "agent-generated hypothesis (unvalidated)"}})
TESTS = {"type": "array", "minItems": 2, "items": _obj(["name", "expected_learning", "feasibility", "cost"], {
    "name": _STR, "expected_learning": {"type": "number", "minimum": 0, "maximum": 1},
    "feasibility": {"type": "number", "minimum": 0, "maximum": 1},
    "cost": {"type": "number", "minimum": 1}})}
CHOICE = _obj(["chosen", "scores", "record_id"], {"chosen": _STR, "scores": {"type": "object"}, "record_id": _STR})
SELECT = _obj(["picks", "record_id"], {"picks": {"type": "array", "minItems": 1}, "record_id": _STR})
RUN_OUT = _obj(["id", "value", "is_hit", "cost", "budget_used", "record_id"], {
    "id": _STR, "value": _NUM, "is_hit": {"type": "boolean"}, "cost": {"type": "integer"},
    "budget_used": {"type": "integer"}, "record_id": _STR})
ANALYSIS_R = _obj(["hypothesis_id", "value", "predicted", "rel_error", "supported", "surprising",
                   "reopened_assumptions", "record_id"], {
    "hypothesis_id": _STR, "value": _NUM, "predicted": _NUM, "rel_error": _NUM,
    "supported": {"type": "boolean"}, "surprising": {"type": "boolean"},
    "reopened_assumptions": {"type": "array", "items": _STR}, "record_id": _STR})
RISK = _obj(["candidate_id", "level", "notes"], {"candidate_id": _STR,
                                                   "level": {"enum": ["low", "medium", "high"]}, "notes": _STR})
