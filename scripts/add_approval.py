"""One-off T011 helper (already applied): approval record entries + README/BUILD_LOG wording."""
import json

README = '''## Human approval (policy ASK): recorded, not enforced as a hard gate
Approval requests are recorded; in our runs they were not enforced as a hard human gate (non-interactive runs decline ASKs automatically; the web run
resolved without a visible card). An interactive REPL run without -p should prompt y/n but is untested.
Evidence (runs/t011-ask, transcript `runs/t011-ask/transcript.jsonl`): (1) the first ASK was declined automatically by the non-interactive `-p` CLI client,
which has no approval handler and fails closed (Omnigent server log ~/.omnigent/logs/server/server-20261004-005242-586707.log line 170;
omnigent_client/_sessions_chat.py:1510). (2) The second call was resolved by the web-UI connection 1 ms after the approval event; the human saw no card and
clicked nothing, having typed "approve" in chat just before. We have NOT shown a policy that waits for a human click. The human decision is record entry `rec-0004`.
The budget DENY policy is the enforced one.
'''
rec = {"record_id": "rec-0005", "kind": "approval_evidence", "run_id": "t011-ask", "seed": 31,
       "evidence": ["first ASK declined automatically by the non-interactive -p CLI client (no approval handler, fails closed): "
                    "~/.omnigent/logs/server/server-20261004-005242-586707.log line 170; omnigent_client/_sessions_chat.py:1510",
                    "second call resolved by the web-UI connection 1 ms after the approval event; no card seen, nothing clicked; "
                    "human had typed 'approve' in chat just before"],
       "conclusion": "not shown to be a policy that waits for a human click; recorded, not a hard gate"}
LOG = ("2026-10-04 T011 correction (coordinator facts): first ASK declined automatically by non-interactive -p client "
       "(fails closed; server log line 170, _sessions_chat.py:1510); second resolved by web-UI connection 1 ms after approval "
       "event, no card, no click. Not a hard gate; rec-0005 added. Interactive REPL untested.\n")

s = open("README.md", encoding="utf8").read()
s = s[:s.index("## Human approval (policy ASK)")] + README
open("README.md", "w", encoding="utf8").write(s)
open("runs/t011-ask/record.jsonl", "a", encoding="utf8").write(json.dumps(rec) + "\n")
open("coord/BUILD_LOG.md", "a", encoding="utf8").write(LOG)
