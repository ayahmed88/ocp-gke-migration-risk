## v46.4-public (2026-11-07)
- `paper/r12_revision_analyses.py` and `paper/results/r12_revision_analyses.json`: Table 5 Holm and Benjamini-Hochberg adjustments; Table 7 label ceiling, criteria-only row, rule count >= 3, service-level bootstrap of the LR-minus-rule-count differences, failure-trained model (Sections 4.2-4.3); selection pool only, holdout closed.
- `paper/external_check/`: blind external check on the 14 records of seven services added to the program after the extract (Section 4.9): pre-specified protocol and frozen manifest committed as 14d6d1c before the ratings were requested, aggregate results table committed as a443ea8, and the two scripts (`stage1_freeze_predictions.py` refuses any input carrying a label or execution-phase column; `stage2_compare.py` verifies the frozen file's SHA-256 before comparing). The 14 records are withheld with the record-level data.
- README and `paper/README.md` describe the external check; version metadata (VERSION, CITATION.cff, README). No change to any experiment, model, rule or official result file.

## v46.3-public (2026-11-05)
- `paper/r11_presubmission_analyses.py` and `paper/results/r11_presubmission_analyses.json`: the analyses added to the November 2026 manuscript (Table 4 High-vs-rest columns, Table 5 criteria-only and heuristic baselines, Table 7 operational value, Table 8 holdout re-summary, Section 4.5 Dev/QA subsets and wave-ordered transfer, calibration, 20-permutation importance of Figure 5), all in the selection pool with the holdout closed; `paper/figures/make_figures.py` updated for the log-loss permutation figure. These files were prepared for the 4 November submission package and were not in the public v46.2-public commit.
- New `paper/results/per_fold_metrics.csv` (25 per-fold values of every metric, model and baseline of Tables 4-6 and Sections 4.3/4.5) and `paper/results/oof_confusion_matrices.json`; no record-level information.
- `paper/r11_presubmission_analyses.py`: the read of the withheld record-level holdout export is guarded; the holdout-bootstrap gate is enabled at the paper's precision; section comments name the manuscript's tables.
- `paper/README.md`: the SD convention statement corrected (the paper reports every ± value with 25 in the denominator, ddof = 0; the corrected resampled t-test uses the sample variance).
- Interface strings (English and Arabic, source and built bundle), `backend/experiments/holdout.py` and the README describe the holdout as a reserved post-selection check, consistent with the paper's Section 3.4, instead of a fully independent sealed evaluation.
- Version metadata (VERSION, CITATION.cff, README). No change to any experiment, model, rule or official result file.

## v46.2-public (2026-11-03)
- Metadata release: the corresponding author's surname is corrected to Shommo in CITATION.cff, LICENSE, README and the English interface footer (source and built bundle), and her ORCID is added to CITATION.cff; version metadata updated. No change to any code path, experiment, model, rule or result file.

## v46.1-public (2026-11-02)
- Data dictionary: Risk_Level and Outcome codebook; Previous_Issues_Count defined per environment. `paper/` folder: re-check, Table 5 SD and round-2 analysis scripts with their result files. README and CITATION.cff with the Zenodo DOIs. No change to any experiment, model, rule or result file of the official run.

## v46-public (2026-11-01)
- Public release for the journal submission. Real dataset, processed table and record-level exports removed; synthetic example workbook added (`data/example/`); dataset path override `MRA_DATASET_XLSX`; evidence tests skip on synthetic data; `paper/` folder with the analysis and figure scripts; README, LICENSE (MIT), CITATION.cff, data dictionary. No change to any experiment, model, rule or result file.

# Changelog — migration-risk-app

Standing rule: every released version ships with its change bullets here
and in the delivery message.

## v45
- Count-up pacing (user feedback: "too fast to even watch"): effort-banner
  counters slowed to 2.4s and now enter as a cascade (each starts 320ms
  after the previous); the Results hero breathes at 1.7s. useCountUp
  gained a start-delay parameter.
- Effort banner: the dismiss (×) control removed (user call) — a showcase
  element has no business hiding itself; it simply lives in presentation
  mode. (Same-version patch per the new iteration rule: fixes within an
  active round land in the current version.)
- M4 Dictionary upgrade: instant search (column/meaning), the 13 official
  pre-execution features highlighted (accent row + "official" chip) with a
  legend line.
- Presentation mode extended: XAI shows top-5 factors per class with the
  permutation card behind a "Full details" expander; Predict renders the
  verdict hero-size with its probability and folds "why" to the top-3
  contributions with a toggle. RTL polish: the ± line and the fingerprint
  block in the Results hero now render LTR-correct inside Arabic.
- Review batch B (approved samples): Exports is now the single thesis-
  figures source — OOF confusion restricted to the 140 pool (single
  repeat, stated in caption); new holdout confusion (22/36, 0.559) with
  table_holdout_predictions.csv; ROC mean±std per class across the 25
  folds (macro 0.859); 4-model seed-stability with Dummy rows persisted
  into the official seed_sensitivity.json via the protocol; drivers and
  the whole global-explanation layer refit on the 140 pool (A2 option 1,
  scope stamped in xai_global.json and shown on the XAI page) while the
  Predict page's local "why" stays on the serving model by design;
  Times-serif, PNG300+SVG, per-figure rich manifest + captions.md; stale
  snapshots are purged on every regeneration; page retitled "Thesis
  figures & tables"; the XAI card now reads the official results live
  (figure literals removed from both locales). Preflight gained the B8
  figures gate (clean-checkout generation + manifest checks) and an
  old-family stale scan with three documented historical exemptions (CHANGELOG, phase4a_winner, influential11_sensitivity — era-stamped archival records).
  Defense-presentation page: numbered progress rail with glowing current
  step (P1) + presenter-cue line per step in presentation mode (P2).
- R6 evidence correction (external review catch, verified): the rulebook's
  R6 headline agreement carried a denominator slip — 93.8% (91/97) instead
  of the true 89.2% (91/102). The strata inside the same line were always
  correct (56/56 at >=4, 35/46 at exactly 3) and can only sum to 91/102.
  rules.yaml now quotes 89.2% (91/102) with both strata; the thesis was
  never affected (it cites only the three 100% rules in §4.5). All eight
  rules' evidence figures were re-derived from the data (R1 118/118,
  R2 120/120, R3 46/46, R4 48/48, R5 15/15, R7 68/93, R8 7/7 — all
  correct) and a permanent guard test (test_rules_evidence.py) now pins
  every quoted figure to a live recount, so evidence lines can never
  silently drift from the data again.
- Methodology-review follow-up (two external reviewer claims verified
  in-repo): (1) Tuning scope — the July Phase-4A study predates the carve
  protocol and ran on all 176 records; verified true, with no effect on
  model choice or deployed parameters (its outcome was to RETAIN the
  pre-declared defaults; nothing in the code reads phase4a outputs).
  tuning.py and phase4a_tuning_folds.json are intentionally preserved
  unchanged as the era-stamped historical study (the thesis v17 §5.10
  resolution cites their forensics). The confirmation rerun from the
  thesis line is now converged into the repo as
  backend/experiments/pool_tuning_check.py: the same nested protocol,
  paired per fold, on the 140-record pool with the vault untouched —
  declared folds must reproduce the official table exactly (asserted),
  and the deltas match the thesis-side run digit for digit (LR +0.004
  modal C=0.2 7/25; XGB -0.008 6/25; RF +0.040 9/25); results in
  pool_tuning_check.json + pool_tuning_summary.json. (2) Feature screen —
  the workbook's exploratory keep-rule (MI + RF + XGB importances vs both
  targets, >=0.02) is label-dependent but selected nothing: all 20
  candidates are KEEP, drops are structural (IDs/constants), and the
  official 13 are availability-determined. New verification
  backend/experiments/feature_screen_check.py recomputes the screen with
  one implementation on 176 vs the 140 pool: 20/20 decisions unchanged
  (feature_screen_pool_check.json).
- Research Progress refresh (thesis writing complete): progress.yaml
  chapter titles verified verbatim against the final thesis v13 (CGS) —
  Ch4 "Analysis & Design", Ch5 "Results & Discussion", Ch6 "Summary &
  Recommendations" — writing items closed (figures 3.1–3.4 and the
  15-figure list confirmed in the docx), list-of-figures bound live to
  auto:exports, and a new "Post-writing — defense preparation" group
  (5 open items) keeps the page an honest roadmap: 43/48 items → 90%.
  Page rebuilt with the presentation skin: hero count-up percentage with
  animated overall bar + chips (items done / groups at 100% / live
  items), an automatic amber "writing complete" milestone line computed
  from the data, per-group count-up percentages with staggered bar
  growth, green ✓ badges on 100% groups, amber styling for the defense
  group, and the editable-path line moved to expert mode.

## v44
- HOTFIX (user-caught crash on first load): Overview called the view-mode
  hook inside JSX after the early loading returns, changing the hook
  count between renders (React #310) and blanking the app. The hook now
  sits unconditionally at the component top; a sweep confirms no other
  page calls a hook inside JSX.

## v43
- THE NEW SKIN + PRESENTATION MODE (approved mock M9+M7, plus M1/M2/M3/
  M5/M6 from the UI/UX audit):
  * Global visual uplift, both themes: gradient + dot-grid backdrop,
    accent glow tokens, page-transition animation, hero-number style.
  * Topbar gains a Presentation/Expert segmented switch (persisted;
    default Presentation). Expert mode keeps every current screen intact.
  * Results, presentation mode: the official config leads with a hero —
    count-up Macro-F1, AUC/accuracy chips, ×-over-baseline line, animated
    model-comparison bars with a glowing leader, the sealed-vault strip
    (live from /api/holdout) and the Low-class caution — with a
    "Full details" expander that reveals the complete expert tables.
  * M1: config raw codes replaced by speaking Arabic/English names with a
    one-line sub everywhere (Results, Live-training group headers, Model
    registry cells); the technical code stays as a small tag/tooltip.
  * M2: a collapsible "About this page" strip on all 14 pages (open by
    default in presentation mode).
  * M3: dotted-underline glossary hints (Macro-F1, AUC, protocol,
    manifest, seed) at the key touchpoints.
  * M5: Overview integrity gates now read as human sentences (raw check
    id kept as tooltip).
  * M6: dismissible "Behind this screen" effort banner on Overview in
    presentation mode, with count-up counters (records, trainings, exams,
    tests, build number from /api/health).

## v42
- M8 (UI/UX audit, finding G6): the XAI page's model-figures line still
  carried the superseded pre-gold numbers (0.608/0.852) in both locales —
  the v34 upgrade updated the Results key but missed this twin key.
  Corrected to the official 0.634±0.109 / AUC 0.859. A full-repo sweep
  confirms no other stale-era literals remain outside the changelog.

## v41
- Replaced the browser-native datalist (unstylable dark popup) with an
  in-app suggestion panel that follows the design system: themed card,
  scrollable, live-filtered by id or service, hover highlight, click to
  pick. The free-case link is now visibly clickable (underlined) and its
  wording softened per user feedback.

## v40
- Step-5 visual polish (user design feedback): the picker's action is now a
  standard solid button, "enter your own case" became a quiet text link,
  and the emoji glyphs were removed from the cluster (buttons + sealed
  note) — the block now speaks the system's design language.

## v39
- Honest three-state mode badge (user-caught wording bug): after a session
  reset the topbar and the Presentation system-card no longer claim
  "Demo mode · saved results"; they show a neutral gray
  "Session reset · awaiting training" until live training / restore
  brings results back. Backend /api/mode now exposes state
  (live | demo | reset); the topbar derives the same truth from the
  status heartbeat it already polls.
- Step-5 vault picker now carries the sealed-vault clarification line
  ("predictions here come from the sealed vault model — independent of
  the training session").
- Verification scenario asserts the badge: gray after reset, green after
  restore.

## v38
- Step-5 vault picker upgraded to a searchable paste-friendly combo
  (user-requested): type or paste a Migration_ID (e.g. copied from the
  vault roster table) with live datalist suggestions; input is normalised
  (case/label-safe) and a localized message explains non-vault ids.

## v37
- Closed the third and last resurrection door (user-caught): the Predict
  page's empty-state button used to call POST /api/models/train-final
  directly, silently rebuilding serving models after an explicit session
  reset. The endpoint now returns 409 while the session is reset (internal
  restore/live-training pipelines are unaffected), and the button now
  navigates to the Live-training page instead of self-training.
- Verification agent scenario now maps ALL post-reset entry doors:
  models list empty, stale-id predict 404, train-final 409, XAI 404,
  vault alive, restore back to 0.634 with serving rebuilt.

## v36
- Step-5 fixes (user-caught within minutes of v35): the "enter your own
  case" button now navigates (the page never received the router prop —
  now passed globally from the shell); the vault picker prefetches the
  roster when the step opens and has a fixed width with a proper
  placeholder (no more collapsing/afterthought resize).
- Demo-integrity restored: the v35 clean-checkout self-heal accidentally
  let serving models resurrect silently after an explicit session reset.
  Self-heal now triggers only when the shipped results manifest exists
  (clean checkout); after a reset, Predict/models honestly wait for live
  training or restore. The sealed vault remains alive after reset BY
  DESIGN (independent judgment layer) — the step-5 vault picker working
  post-reset is correct and documented.
- Verification agent upgraded with --scenario: machine-checks the full
  session logic (reset emptiness, vault independence, XAI guard, restore
  back to the official 0.634 with serving rebuilt) before any release.

## v35
- Clean-checkout self-heal: serving models now build automatically on first
  demand (deterministic, mirrors the vault pattern) — a fresh unzip passes
  the full 21-test suite with no manual step; preflight gained a --clean
  mode that proves it.
- Predict page: model list deduplicated (latest per algorithm), ordered and
  defaulted to the official primary "Logistic Regression (primary)"; RF is
  labelled the high-sensitivity alternative (High recall 0.892), XGBoost
  "for comparison". Presentation system-card now reports the primary LR,
  not the last-trained model.
- Guided walkthrough step 5 upgraded to three freedom tiers: the scripted
  MIG-006 button, a free picker over all 36 sealed-vault records with live
  prediction and truth check (new POST /api/holdout/predict_case), and a
  jump to the fully free Predict page.
- Documentation debt from the audit: stale v20 lines rewritten (README
  header + acceptance-checklist snapshot note), the tuning sentence now
  states the truth (evaluated & rejected, defaults retained), a First-run
  section added, and the Low-class limitation is now flagged in README and
  on the Results page (15 records / 11 services — directional only).

## v34
- METHODOLOGY UPGRADE (decision B, user-approved): the 20% service vault is
  now carved BEFORE any model comparison; all selection experiments run on
  the 80% pool only (140 rows / 70 services), making the sealed holdout a
  fully independent confirmatory test. Vault identity and its sealed report
  are byte-identical (18 services / 36 records, Macro-F1 0.559, 22/36).
- New official selection results (pool=140): LR 0.634±0.109 / AUC 0.859 /
  acc 0.709 (winner, now leading on all three metrics at ALL seed bases
  42/7/100/2026); XGBoost 0.592±0.135; Random Forest 0.539±0.141
  (High-recall 0.892 — high-sensitivity alternative; weak Low-recall 0.227
  documented); Dummy 0.238. Previous full-pool figures (0.608 family) are
  superseded and remain only as CHANGELOG history.
- Manifest now records the selection_pool; shared carve helper
  (experiments/split.py) feeds both the runner and the vault so they can
  never drift. Serving models are refit on all 176 post-protocol
  (documented in the registry entries).

## v33
- Presentation page now shows the live last-run seed too (system card and
  the methodology sentence), completing the sweep v32 missed; a repo-wide
  scan confirms no hardcoded seed display remains in the UI source.
- New scripts/preflight.py: pre-release verification agent (full test
  suite + stale-literal UI scan + API smoke incl. holdout-seal check).
  Standing rule: no version ships without a green preflight in the
  delivery message.

## v32
- The last-run seed now reflects in EVERY place a seed is displayed
  (user-reported after v31): topbar badge (amber when custom), Training
  protocol subtitle ("... seed 777 (declared 42)"), and the Results
  manifest card (previously printed the static config seed). Also fixed a
  precedence bug where, while a custom-seed run was in progress, the stale
  manifest's old seed overrode the live one in the status payload. The
  sealed vault remains seed-42 by design.

## v31
- The seed of the last experiment is now visible everywhere it matters:
  finish chip and idle banner on the Training page ("... · seed 777 · ...")
  and a dedicated line atop the Evaluation results page, all sourced from
  the experiment manifest (split_seed_base) / live job state. Custom-seed
  runs are therefore visibly credited on screen, closing the "field works
  but 42 still shows" confusion; the protocol subtitle remains the fixed
  pre-declared methodology banner by design.

## v30
- Live training now completes the full session trilogy (experiment ->
  serving models -> XAI cache), exactly like restore. Before v29 the XAI
  page's silent lazy rebuild masked this gap; the v29 guard exposed it
  (user-reported: results present but XAI empty after a Training-page run).
- Serving models and explanations are always rebuilt in the official
  declared configuration; a custom experiment seed affects the experiment
  tables only.

## v29
- Demo-integrity fix (user-caught): after a session reset, opening the XAI
  page used to silently retrain a full LR + recompute permutation importance
  and show data as if nothing was cleared. /api/explain/global now returns a
  polite 404 until live training or restore rebuilds the cache; the page
  shows a localized empty state. Explicit force=True (restore pipeline)
  unchanged.
- Documented the definitive reset matrix (what empties vs. what survives).

## v28
- Critical fix (defense-day): "Reset demo session" now also clears the
  server's in-memory job state (status, completed-model table, timer,
  last-run timestamp). Previously only files were deleted, so the Live
  Training page rehydrated a ghost results table from memory after reset.
- Verified end-to-end: reset -> Training page truly blank (idle, no rows,
  no timestamp, results 404) -> one-click restore rebuilds everything with
  identical numbers.

## v27
- Dataset is now downloadable from the UI: `GET /api/dataset/download`
  serves the raw Excel; buttons added on the Overview page and in the
  Quick-guide resources card.
- Overview gained a one-click path to the 27-column documentation
  ("Data dictionary" shortcut) — answering "what are the 27?" in place.
- Quick-guide "Exports" now navigates to the in-app Exports page
  (Chapter-4 figures & tables) instead of opening the raw manifest JSON.

## v26
- Vault transparency (approved): new "Vault records (36)" toggle inside the
  Presentation holdout card + `GET /api/holdout/records` — the full sealed
  roster (service, record, environment, expert label, vault-model
  prediction, hit/miss), derived deterministically from the seed and
  verified against the sealed confusion matrix on every call.
- Fixed "manual not found in docs/": the user-manual and interview-guide
  DOCX files carried Arabic filenames inside the release zip, which Windows
  extraction garbles; renamed to ASCII (System_User_Manual_AR.docx,
  supervisor/Interview_Algorithms_Guide_AR.docx) per the packaging rule —
  Arabic stays inside the content, never in file names.

## v25
- Last-run timestamp for credibility: the finished chip now shows
  "done in Xs · YYYY-MM-DD · HH:MM", and an always-on banner shows
  "Last training: <date · time> — done in Xs" even after a server restart
  (persisted via the experiment manifest, which now also records
  `wall_seconds`).
- Status endpoint: new `last_run_at` / `last_wall_s` fields (in-memory when
  fresh, manifest fallback otherwise).
- Decision recorded: no "demo-light" training mode — the full 300-fold run
  (~45 s on the native Python path) is the single, honest live demo.

## v24
- Added this CHANGELOG.md (versions v17+ documented retroactively).
- README: new "Performance notes (Windows)" section — native venv is the
  fast path (reference: full 300-fold experiment ≈ 46 s on a 1-core Linux
  box); Docker Desktop/WSL2 resource settings; AC power / High-performance
  plan advice; `docker compose restart` clears a stuck in-memory job.
- No code or methodology changes.

## v23
- Completed-model rows now rehydrate after navigating away and after
  completion (server keeps per-run model summaries in job state).
- "Remaining ≈" estimate adapts to the pace of the last 8 folds instead of
  the global average.
- Quick-guide texts rewritten in a neutral documentation voice (presenter
  notes removed from public UI).
- New "User manual (Word)" download button (`GET /api/docs/manual`) and a
  clearly labeled "API reference (Swagger)" link.

## v22
- Server-side source of truth for the training lifecycle: elapsed time,
  final duration, and progress (N/300) computed and served by the backend.
- Live-training page resumes the timer and progress after navigation;
  "last run finished in ..." banner with a shortcut to Evaluation results.
- Standardized 409 "already running" responses across start/restore.

## v21
- Viewport-locked frame: header and footer pinned; only the content column
  scrolls (graceful fallback on narrow screens).

## v20
- Phase 6 acceptance: 15-test end-to-end suite (one per UI page + SPA
  shell), docs/ACCEPTANCE_CHECKLIST.md, bilingual academic footer.

## v19
- Presentation control panel: guarded session reset + one-click restore.
- Live training timer; random unseen-case tester drawing from the sealed
  20% vault (persistent vault model survives resets).
- File vault: versioned uploads with notes, history, and downloads.

## v18
- Research-progress update (supervisor-deliverables group, robustness
  item); docs/ bind-mounted in compose so progress edits reflect on
  refresh.

## v17
- Split-seed control: APP_SEED env override + optional per-run seed field;
  seed recorded in the experiment manifest; seed-sensitivity evidence
  (bases 42/7/100/2026).
