"""Cached direct LLM path via the logged-in `claude -p` CLI (subscription; no API key is read).

Cache key = (prompt, model, seed). Runs from a temp cwd with no tools and a fixed system prompt so that no
project files/CLAUDE.md enter the context. Temperature cannot be set through the CLI (default sampling); the cache
makes every evaluation run reproducible. Any non-zero exit / limit message raises Throttled: callers must STOP, no retries.
"""
import json
import subprocess
import tempfile
import threading

from .cache import Cache

SYSTEM = "You are a materials-science estimator. Reply with the requested JSON only, no prose."
_lock = threading.Lock()
STATS = {"calls": 0, "cached": 0, "usd": 0.0}


class Throttled(RuntimeError):
    pass


def ask(prompt, model="claude-sonnet-5-5", seed=0, cache_dir="runs/t009/cache"):
    cache = Cache(cache_dir)

    def call():
        p = subprocess.run(
            ["claude", "-p", "--model", model, "--tools", "", "--system-prompt", SYSTEM,
             "--output-format", "json", prompt],
            capture_output=True, text=True, encoding="utf-8", cwd=tempfile.gettempdir(), timeout=300)
        out = (p.stdout or "").strip()
        try:
            d = json.loads(out)
        except Exception:
            raise Throttled(f"non-JSON CLI output (rc={p.returncode}): {(out or p.stderr)[:200]}")
        if p.returncode != 0 or d.get("is_error"):
            raise Throttled(f"CLI error rc={p.returncode}: {str(d.get('result'))[:200]}")
        with _lock:
            STATS["calls"] += 1
            STATS["usd"] += float(d.get("total_cost_usd") or 0)
        return {"text": d["result"], "usd": d.get("total_cost_usd")}

    hit_before = STATS["calls"]
    r = cache.get_or_call(prompt, model, seed, call)
    if STATS["calls"] == hit_before:
        with _lock:
            STATS["cached"] += 1
    return r["text"]


def parse_json(text):
    s = text.strip()
    if s.startswith("```"):
        s = s.strip("`")
        s = s[s.find("\n") + 1:] if s.lower().startswith("json") else s
    a = min([i for i in (s.find("{"), s.find("[")) if i >= 0], default=0)
    b = max(s.rfind("}"), s.rfind("]")) + 1
    return json.loads(s[a:b])
