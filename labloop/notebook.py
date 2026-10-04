"""Lab notebook: append-only record of every experiment, hypothesis change and decision.

Negative results are stored exactly like positive ones: they are what make the
next decision smarter.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class Notebook:
    def __init__(self, path: str | Path = ":memory:"):
        self.db = sqlite3.connect(str(path))
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS experiments(
            id TEXT PRIMARY KEY, round INT, formula TEXT, comp_key TEXT, purpose TEXT,
            hypothesis TEXT, ok INT, bandgap REAL, log_t80 REAL, phase TEXT,
            cost REAL, surprise REAL, protocol TEXT);
        CREATE TABLE IF NOT EXISTS hypothesis_events(
            round INT, hypothesis TEXT, event TEXT, detail TEXT);
        CREATE TABLE IF NOT EXISTS decisions(
            round INT, mode TEXT, rationale TEXT, slots TEXT);
        """)

    def log_experiment(self, rnd: int, e: dict):
        r = e["result"]
        self.db.execute("INSERT OR REPLACE INTO experiments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            e["id"], rnd, e["formula"], e["key"], e["purpose"], e.get("hypothesis"), int(r["ok"]),
            r["bandgap_ev"], r["log_t80"], r["phase"], r["cost"], e.get("surprise"),
            json.dumps(e["protocol"])))

    def log_hypothesis(self, rnd: int, hid: str, event: str, detail: str = ""):
        self.db.execute("INSERT INTO hypothesis_events VALUES (?,?,?,?)", (rnd, hid, event, detail))

    def log_decision(self, rnd: int, mode: str, rationale: str, slots: list):
        self.db.execute("INSERT INTO decisions VALUES (?,?,?,?)", (rnd, mode, rationale, json.dumps(slots)))

    def commit(self):
        self.db.commit()

    def negative_results(self) -> list[tuple]:
        return self.db.execute("SELECT formula, phase FROM experiments WHERE ok = 0").fetchall()
