# T011 human-approval evidence (interactive REPL run)
- Run: agents/policy_demo.yaml, `omnigent run ... --server local` WITHOUT -p (interactive REPL), seed 32, budget 2, run_id t011-repl, session 99bf26c91e944ae6a5cf512966da0243.
- Human report: the REPL paused with an approval prompt before step 4 (recommend_for_validation); the human typed `y`.
- Server log (~/.omnigent/logs/server/server-20261004-010932-392914.log, local time): 01:10:00.41 tool call reaches the server (policy ASK);
  01:10:01.999 elicitation resolved by the web-UI (browser) connection, port 50369, which was open during the run; 01:10:02.012 a second resolve from the REPL client (python-httpx, port 51825); 01:10:02.029 tool executes -> record rec-0003. (Correction after Scout review: an earlier version wrongly attributed port 50369 to the REPL.)
- Conclusion: in this interactive run the approval policy held the tool call (~1.6 s) until a client answered; the human typed y in the REPL, but the browser's resolve arrived first, so this run does not prove the hold lasts until a human answers. Airtight test still owed: REPL only, web UI closed, wait >= 30 s before answering. Non-interactive `-p` runs decline ASKs automatically (fail-closed; see runs/t011-ask). The earlier web-UI run resolved without a visible card and is not counted as a human gate.
- Transcript: transcript.jsonl (runner token id redacted).
