"""SQLite belief state: hypotheses, experiments, decisions."""
import json
import sqlite3

DDL = """
CREATE TABLE IF NOT EXISTS hypotheses(id TEXT PRIMARY KEY, body TEXT, score REAL DEFAULT 0, status TEXT DEFAULT 'open');
CREATE TABLE IF NOT EXISTS experiments(n INTEGER PRIMARY KEY AUTOINCREMENT, hypothesis_id TEXT, x REAL, y REAL, cost INTEGER);
CREATE TABLE IF NOT EXISTS decisions(n INTEGER PRIMARY KEY AUTOINCREMENT, action TEXT, reason TEXT);
"""


class Belief:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path)
        self.db.executescript(DDL)

    def add_hypotheses(self, hs):
        for h in hs:
            self.db.execute("INSERT OR REPLACE INTO hypotheses(id,body) VALUES(?,?)", (h["id"], json.dumps(h)))
        self.db.commit()

    def open_hypotheses(self):
        return [json.loads(b) for (b,) in self.db.execute("SELECT body FROM hypotheses WHERE status='open'")]

    def record(self, hid, res, analysis):
        self.db.execute("INSERT INTO experiments(hypothesis_id,x,y,cost) VALUES(?,?,?,?)",
                        (hid, res["x"], res["y"], res["cost"]))
        self.db.execute("UPDATE hypotheses SET score=score+?, status=? WHERE id=?",
                        (1.0 if analysis["supported"] else -1.0,
                         "open" if analysis["supported"] else "refuted", hid))
        self.db.commit()

    def log_decision(self, d):
        self.db.execute("INSERT INTO decisions(action,reason) VALUES(?,?)", (d["action"], d["reason"]))
        self.db.commit()

    def experiments(self):
        return self.db.execute("SELECT hypothesis_id,x,y,cost FROM experiments ORDER BY n").fetchall()

    def best(self):
        return self.db.execute("SELECT MAX(y) FROM experiments").fetchone()[0]
