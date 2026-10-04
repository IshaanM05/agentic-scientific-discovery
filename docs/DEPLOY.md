# Deploying the live demo (human step)

The demo is one self-contained file, `docs/index.html` (no build, no network calls, no secrets). It is rebuilt offline by `python scripts/build_dashboard.py` from `dashboard/template.html` and the committed `runs/*`, including any `runs/ll-*` LabLoop Omnigent runs.

## Vercel (uses `vercel.json`: no build, serves `docs/`)
1. vercel.com > Add New > Project > import `IshaanM05/agentic-scientific-discovery`.
2. Production branch: the branch to submit (after the lead merges, `main`). Framework preset: Other. Leave build and install commands empty; output directory is read from `vercel.json` (`docs`).
3. Deploy. The live URL serves `docs/index.html` at `/`.
CLI alternative: `npx vercel --prod` from the repo root.

## GitHub Pages (fallback)
Settings > Pages > Source: branch, folder `/docs`. URL: `https://ishaanm05.github.io/agentic-scientific-discovery/`.

## Replit (second fallback)
Import the repo into Replit (Create Repl > Import from GitHub). `.replit` and `replit.nix` serve `docs/` with `python3 -m http.server 8000`; for a permanent URL choose Deploy > Static (public dir `docs`, set in `.replit`). Nothing to install and no secrets.

## Before submitting
- Rebuild after the last `runs/ll-*` commit: `python scripts/build_dashboard.py`, then commit `docs/index.html`.
- Open the live URL in a private window; confirm the "Omnigent runs" tab lists the runs (or says none are committed).
- Paste the URL into README "Live demo" and the submission form.
- Offline replay with more detail: `streamlit run dashboard/app.py`.
