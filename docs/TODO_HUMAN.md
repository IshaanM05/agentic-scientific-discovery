# TODO for humans (things that cannot be done in the cloud)

Deadline: Sun Oct 4, 9:00 AM ET (submission). Code freeze 06:00 ET. Work top to bottom; items 1-6 block the submission. Commands assume a clone of `IshaanM05/agentic-scientific-discovery` on branch `final/submission`.

## Ordered list

1. **Run the live Omnigent golden runs that are missing** (owner: lead, local machine with the subscription login). `runs/ll-w2000`, `runs/ll-w2001`, `runs/ll-w2002` are NOT in the repo (checked on every remote branch), so every "Omnigent vs baseline" number is still open (see section "Markers left open").
   ```
   powershell -ExecutionPolicy Bypass -File scripts/live.ps1 agents/labloop_planner.yaml "Call ll_start(world=2000, seed=0, budget=60) and run the full LabLoop loop to stop or budget. Follow your prompt."
   ```
   Set `$env:ASD_RUN_DIR="runs/ll-w2000"; $env:ASD_RUN_ID="ll-w2000"` first; repeat with 2001 and 2002 and fresh dirs. Then `grep -E "eg_true|lt_true|true_hit" runs/ll-w2000/*` must print nothing. Then run `python scripts/ll_compare.py`, `python scripts/build_dashboard.py`, `python scripts/make_kg.py`, and fill the open markers listed below from `docs/RESULTS_LABLOOP.md` section 5. Commit and push to `final/submission`.
2. **Rotate the subscription token that was exposed earlier** (owner: lead). Run `claude setup-token` (or log out and in on the account), revoke the old token in the account settings, update the local gitignored `.env`. Confirm with `git grep -n -i -E "sk-ant|oauth.*=[A-Za-z0-9]"` that no token is committed (the 2026-10-04 sweep found none in the tree; history was not scanned for the earlier exposure, so also run `git log -p --all -S"sk-ant" | head`).
3. **Deploy `docs/` to Vercel** (owner: deploy person). Import the repo at vercel.com/new, Framework "Other", Build command empty, Output directory `docs`. (`vercel.json` already serves `docs/` statically; details in `docs/DEPLOY.md`.) Replit is the fallback (`replit.nix` is in the repo). Open the URL and check the "Omnigent runs" tab, the LabLoop panel and the link to `kg.html`.
4. **Paste the live URL** into `README.md` (the line marked `[HUMAN: paste Vercel URL]`), `docs/index.html` footer if desired, and `docs/SUBMISSION_CHECKLIST.md`. Commit and push.
5. **Record the three videos** (owner: recording person) with `docs/VIDEO_SCRIPTS.md`: demo (2 minutes, `docs/DEMO_SCRIPT.md`), tech video, team video. Do not say "faster" or "acceleration" about the steel result; say "hard gate" for approval only with "in interactive runs". Use only numbers that appear in `README.md`, `docs/RESULTS_LABLOOP.md` or committed runs. Upload each to a link you can paste (YouTube unlisted or Drive with link access).
6. **Fill names and roles** in the team section of `README.md` (placeholders `[HUMAN: name, role]`).
7. **Accounts and team**: every team member needs an account on app.hack-nation.ai and must be added under "team & submission" (owner: deploy person; each member confirms their own login).
8. **Submit on app.hack-nation.ai AND the Google form** (owner: deploy person): three video links, the public repo link, the live demo link, and the project description (use `docs/PITCH.md`). Do both; the brief says the same items go to both.
9. **Discord**: tell the organizers which challenge we chose (Challenge 3, Agentic Scientific Discovery) at tinyurl.com/7-HN-Discord (owner: any member; one message is enough).
10. **Confirm the repo is public** (owner: reviewer): open `https://github.com/IshaanM05/agentic-scientific-discovery` in a private browser window; or Settings, General, Danger zone, Change visibility. Check there is no `.env`, token or organizer deck in the tree (`git ls-files | grep -E "\.env|\.pptx|docs/reference"` prints nothing).
11. **Merge the final branch into `main`** (owner: reviewer, only after items 1-10 are done and the lead says OK). Commit authorship: 17 commits from the worker branches carry the author identity "Claude <noreply@anthropic.com>" (`git log --format='%an' | sort | uniq -c`). If the no-AI-mention rule should cover authorship, do NOT merge those commits as they are. Use a squash merge with a human author:
    ```
    git checkout main && git pull
    git merge --squash origin/final/submission
    git commit -m "Hack-Nation Challenge 3 submission" --author "Name <email>"
    git push origin main
    ```
    Run `python -m pytest -q` first (the omnigent import tests need Python 3.12 with `pip install -r requirements.txt`).
12. **Delete remote worker branches after confirming their content is merged** (owner: reviewer): `final/submission` contains `w1`..`w4`, `w6`..`w8`, `w10` (see `docs/FINAL_HANDOFF.md` for head SHAs; `git diff origin/final/submission origin/<branch> --stat` should show only files that final/submission already changed later). Then `git push origin --delete w1/labloop-tools w2/labloop-results w3/labloop-demo w4/labloop-multifidelity w6/pitch-materials w7/claims-audit w8/knowledge-graph w10/stat-tightening labloop-mvp labloop-v2 integration/labloop`. Keep `dev/agentic-loop` until main is updated. There is no `w5/labloop-report` branch on the remote: if W5's report exists elsewhere, merge it before deleting anything.
13. **Optional, if time**: rerun the large LabLoop benchmark with the exact interpreter that will be used for the claim (`python scripts/ll_big_benchmark.py`, about an hour on 4 cores) and compare with `docs/RESULTS_LABLOOP_BIG.md`.

## Markers left open (needs the live golden runs; item 1)
These cannot be filled from committed files today. Each is still present in the file as a `[TO FILL: ...]` marker naming the source:
- `docs/DEMO_SCRIPT.md` row 1:32-1:52: final live run `runs/ll-w2000` (world, seed, units used, hits, units to first hit, replicated discoveries, refutations, ADAPT events).
- `docs/PITCH.md`, `docs/VIDEO_SCRIPTS.md`, `docs/JUDGE_GUIDE.md`, `docs/QA_PREP.md`: any statement that compares the Omnigent team with the rule-based baseline on worlds 2000-2002, and the count of Omnigent ADAPT events.

## Teammate tasks (three people; assign by availability, no names assumed)
**Person A: recording and videos.** Item 5 (demo, tech and team videos), item 6 (names and roles text for the team video), and the voice-over checks against `docs/DEMO_SCRIPT.md` "Must not say". Hand the three video links to Person B.
**Person B: deploy and submission forms.** Items 3, 4, 7, 8, 9. Needs the video links from Person A and the final README from Person C.
**Person C: final review and repo check.** Items 10, 11, 12, plus a read of `docs/FINAL_HANDOFF.md` "Known issues" and the claims check (`python scripts/check_claims.py --strict` must exit 0), a clean-clone run of `bash scripts/reproduce.sh` (or the `.ps1`), and a last look for secrets and hidden-truth names (commands in `docs/FINAL_HANDOFF.md`). The lead (item 1 and 2) can be any of the three; whoever holds the Omnigent login does it.
