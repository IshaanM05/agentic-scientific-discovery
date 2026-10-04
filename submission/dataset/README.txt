Princeton-Plainsboro dataset (Hack-Nation Challenge 03)
=======================================================

All synthetic data is regenerated exactly by the code (seeds in configs/experiment.yaml).
Real data comes from public NASA archives; target names are anonymized (K-####).

raw/
  koi_cumulative_subset.csv   NASA Exoplanet Archive "cumulative" KOI table subset, as downloaded.
      kepid, kepoi_name         Kepler IDs (NOT exposed to agents)
      koi_disposition           archive disposition (CONFIRMED / CANDIDATE / FALSE POSITIVE)
      koi_fpflag_nt/ss/co/ec    archive false-positive flags (treated as labels and stripped)
      koi_period [d], koi_time0bk [BKJD], koi_duration [h], koi_depth [ppm], koi_model_snr
      koi_srad [R_sun], koi_slogg [cgs], koi_steff [K]

processed/
  <set>_targets.csv           one row per target; <set> = synthetic_calibration (600), synthetic_blind (240),
                              real_kepler (48)
      target_id                 anonymized ID (C-#### calibration, T-#### blind, K-#### real)
      period_d, epoch           orbital period [days], mid-transit time of first transit [days]
      duration_h, depth_ppm     transit duration [hours], depth [parts per million]
      snr                       detection signal-to-noise ratio
      teff_k, radius_rsun, mass_msun, logg   catalog stellar parameters
      rho_cat, rho_err_dex      catalog stellar density [g/cm^3] and its uncertainty [dex]
      label                     ground truth: H1 planet, H2 eclipsing binary, H3 blended background EB,
                                H4 stellar variability/spots, H5 instrumental artifact.
                                Real set: "H4|H5" = archive "not transit-like" (the two can't be separated).
  <set>_lightcurves.npz       NumPy archive, keys "<target_id>__<field>" with fields:
      time [days], flux (normalized), flux_err, quality (bool, True = flagged cadence),
      cen_x, cen_y (flux-weighted centroid offsets [pixels])
      Load:  d = np.load(path); d["T-0167__flux"]

output/
  records.jsonl               benchmark: one record per (condition, target, stopping threshold) on the blind set
  real_records.jsonl          same on the 48 real Kepler KOIs
  b0_llm.jsonl                single-LLM baseline (Claude Sonnet 5.5) on the first 40 blind targets
  likelihood_tables.json      P(test outcome | hypothesis) calibrated on the calibration split only
  summary.json, real_summary.json   aggregate metrics behind results/REPORT.md and REAL_REPORT.md
  label_access_audit.json     Data Gatekeeper audit: label reads by caller (0 by agents)

License/attribution: Kepler data courtesy of NASA Exoplanet Archive and MAST (STScI).
