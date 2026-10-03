"""JSON schemas for every agent output in the loop."""
from jsonschema import validate

HYPOTHESIS = {
    "type": "object",
    "required": ["id", "text", "x_pred", "prediction"],
    "properties": {
        "id": {"type": "string"},
        "text": {"type": "string"},
        "x_pred": {"type": "number"},
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
