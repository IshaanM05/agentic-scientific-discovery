# TODO for humans (things that cannot be done in the cloud)

Deadline: Sun Oct 4, 9:00 AM ET (submission). Code freeze 06:00 ET. Work top to bottom; items 1-5 block the submission. Commands assume a clone of `IshaanM05/agentic-scientific-discovery` on branch `final/submission`.

## Ordered list

1. **Rotate the subscription token that was exposed earlier** (owner: lead). Run `claude setup-token` (or log out and in on the account), revoke the old token in the account settings, update the local gitignored `.env`. Confirm with `git grep -n -i -E "sk-ant|oauth.*=[A-Za-z0-9]"` that no token is committed (the sweeps found none in the tree; history was not scanned for the earlier exposure, so also run `git log -p --all -S"sk-ant" | head`).
2. **Deploy `docs/` to Vercel** (owner: deploy person). Import the repo at vercel.com/new, Framework "Other", Build command empty, Output directory `docs`. (`vercel.json` already serves `docs/` statically; details in `docs/DEPLOY.md`.) Replit is the fallback (`replit.nix` is in the repo). Open the URL and check the "Omnigent runs" tab, the LabLoop panel and the link to `kg.html`.
3. **Paste the live URL** into `README.md` (the line marked `[HUMAN: paste Vercel URL]`), `docs/index.html` footer if desired, and `docs/SUBMISSION_CHECKLIST.md`. Commit and push.
4. **Record the three videos** (owner: recording person) with `docs/VIDEO_SCRIPTS.md`: demo (2 minutes, `docs/DEMO_SCRIPT.md`), tech video, team video. Do not say "faster" or "acceleration" about the steel result; say "hard gate" for approval only with "in interactive runs". Use only numbers that appear in `README.md`, `docs/RESULTS_LABLOOP.md` or committed runs. Upload each to a link you can paste (YouTube unlisted or Drive with link access).
5. **Fill names and roles** in the team section of `README.md` (placeholders `[HUMAN: name, role]`).
6. **Accounts and team**: every team member needs an account on app.hack-nation.ai and must be added under "team & submission" (owner: deploy person; each member confirms their own login).
7. **Submit on app.hack-nation.ai AND the Google form** (owner: deploy person): three video links, the public repo link, the live demo link, and the project description (use `docs/PITCH.md`). Do both; the brief says the same items go to both.
8. **Discord**: tell the organizers which challenge we chose (Challenge 3, Agentic Scientific Discovery) at tinyurl.com/7-HN-Discord (owner: any member; one message is enough).
9. **Confirm the repo is public** (owner: reviewer): open `https://github.com/IshaanM05/agentic-scientific-discovery` in a private browser window; or Settings, General, Danger zone, Change visibility. Check there is no `.env`, token or organizer deck in the tree (`git ls-files | grep -E "\.env|\.pptx|docs/reference"` prints nothing).
10. **Merge the final branch into `main`** (owner: reviewer, only after items 1-9 are done and the lead says OK). Commit authorship: 28 commits from the worker branches carry the author identity "Claude <noreply@anthropic.com>" (`git log --format='%an' | sort | uniq -c`). If the no-AI-mention rule should cover authorship, do NOT merge those commits as they are. Use a squash merge with a human author:
    ```
    git checkout main && git pull
    git merge --squash origin/final/submission
    git commit -m "Hack-Nation Challenge 3 submission" --author "Name <email>"
    git push origin main
    ```
    Run `python -m pytest -q` first (the omnigent import tests need Python 3.12 with `pip install -r requirements.txt`).
11. **Delete remote worker branches after confirming their content is merged** (owner: reviewer): `final/submission` contains `w1`..`w4`, `w6`..`w8`, `w10` (see `docs/FINAL_HANDOFF.md` for head SHAs; `git diff origin/final/submission origin/<branch> --stat` should show only files that final/submission already changed later). Then `git push origin --delete w1/labloop-tools w2/labloop-results w3/labloop-demo w4/labloop-multifidelity w12/ll-w2000 w12/ll-w2001 w12/ll-w2002 w5/labloop-report claude/w5-labloop-report-t1kxni w6/pitch-materials w7/claims-audit w8/knowledge-graph w10/stat-tightening labloop-mvp labloop-v2 integration/labloop`. Keep `dev/agentic-loop` until main is updated. `w5/labloop-report` (0ad95b7) is merged; its duplicate `claude/w5-labloop-report-t1kxni` points at the same commit and can be deleted with it. `origin/claude/final-submission-s40w5c` is a session branch: delete it after `final/submission` is merged.
12. **Optional, if time**: rerun the large LabLoop benchmark with the exact interpreter that will be used for the claim (`python scripts/ll_big_benchmark.py`, about an hour on 4 cores) and compare with `docs/RESULTS_LABLOOP_BIG.md`.

## Live runs: done, with one optional follow-up
Live Omnigent runs now exist for worlds 2000 (`runs/ll-w2000-full` complete; `runs/ll-w2000` partial), 2001 (`runs/ll-w2001`) and 2002 (`runs/ll-w2002`), plus smoke runs; no `[TO FILL]` marker is left. Optional, only if someone has quota and wants a stronger comparison: the 2001 and 2002 runs ended early (planner decision, LabLoop stop rule), so they are not comparable to the baseline at 60 units, and each world has one seed. More seeds need a fresh directory each, e.g. `$env:ASD_RUN_DIR="runs/ll-w2002-s1"; $env:ASD_RUN_ID="ll-w2002-s1"` then `powershell -ExecutionPolicy Bypass -File scripts/live.ps1 agents/labloop_planner.yaml "Call ll_start(world=2002, seed=1, budget=60) and run the full LabLoop loop to stop or budget. Follow your prompt."`, then `grep -E "eg_true|lt_true|true_hit" runs/ll-w2002-s1/*` (must print nothing) and `python scripts/ll_compare.py`.

## Teammate tasks (three people; assign by availability, no names assumed)
**Person A: recording and videos.** Item 4 (demo, tech and team videos), item 5 (names and roles text for the team video), and the voice-over checks against `docs/DEMO_SCRIPT.md` "Must not say". Hand the three video links to Person B.
**Person B: deploy and submission forms.** Items 2, 3, 6, 7, 8. Needs the video links from Person A and the final README from Person C.
**Person C: final review and repo check.** Items 9, 10, 11 (and the optional 12), plus a read of `docs/FINAL_HANDOFF.md` "Known issues" and the claims check (`python scripts/check_claims.py --strict` must exit 0), a clean-clone run of `bash scripts/reproduce.sh` (or the `.ps1`), and a last look for secrets and hidden-truth names (commands in `docs/FINAL_HANDOFF.md`). Token rotation (item 1) is done by whoever holds the account login.
