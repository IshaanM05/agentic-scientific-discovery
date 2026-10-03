# T011 airtight approval test (human-run; server-log times are local)
- Run: agents/policy_demo.yaml, interactive (no -p), seed 33, budget 2, run_id t011-repl30, session 40a88228247c4b82bf161f24af3b566a.
- Server log ~/.omnigent/logs/server/server-20261004-012155-798994.log (local time):
  - 01:22:31.125 recommend_for_validation reaches the server; human_approval policy returns ASK.
  - 01:22:31 to 01:22:53: no resolve from any client; only /health heartbeats (01:22:37, 01:22:47). The call is held.
  - 01:22:53.336 the elicitation is resolved by a new client connection when the human clicks Approve (human report: waited ~30 s by counting).
  - 01:22:53.370 the tool executes -> record rec-0003.
- Measured hold: 22.2 s, ended only by the human's action. Nothing resolved the ASK automatically.
- Conclusion: in an interactive run, the approval policy holds the tool call until a human answers.
- Transcript: transcript.jsonl (runner token id redacted).
