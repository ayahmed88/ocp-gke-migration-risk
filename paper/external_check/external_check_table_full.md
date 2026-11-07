# External check — aggregate results (stage 2, run 7 Nov 2026; predictions frozen 2026-11-06T21:57:15 UTC, sha256 601c6be2…)

Quantities of PROTOCOL.md Section 3 (counts only; no record-level information). Pre-specified interval: the Clopper-Pearson interval of the LR row only; the intervals shown for the other models are a by-product of the script and were not pre-specified.

| Model or policy | 1. Predicted level equals recorded level (of 14) | 2. High versus rest |
|---|---|---|
| LR, 13 attributes (serving model) | 9/14 (95% CI 0.351-0.872); Dev 4/7, QA 5/7 | recorded High flagged 7/9; non-High not flagged 4/5 |
| LR on rule-trigger count (Table 5 baseline) | 11/14 (95% CI 0.492-0.953); Dev 4/7, QA 7/7 | recorded High flagged 8/9; non-High not flagged 5/5 |
| Flag: rule-trigger count >= 3 (Table 7 policy) | - | recorded High flagged 8/9; non-High not flagged 5/5 |
| LR on the five documented criteria | 10/14 (95% CI 0.419-0.916); Dev 4/7, QA 6/7 | recorded High flagged 6/9; non-High not flagged 5/5 |
| Random Forest, 13 attributes (secondary) | 9/14 (95% CI 0.351-0.872); Dev 4/7, QA 5/7 | recorded High flagged 6/9; non-High not flagged 4/5 |
| XGBoost, 13 attributes (secondary) | 10/14 (95% CI 0.419-0.916); Dev 5/7, QA 5/7 | recorded High flagged 7/9; non-High not flagged 5/5 |

| 4. Outcomes | n | LR predicted High | rule count >= 3 flagged |
|---|---|---|---|
| Failed first attempt | 1 | 1 | 1 |
| Delayed | 9 | 5 | 6 |

5. Rule consistency: fired set identical to the recorded actions for 7/14 records (R5 not evaluable before execution; R8 fallback not compared).

| Rule | fired, not recorded | recorded, not fired |
|---|---|---|
| R1 | 0 | 0 |
| R2 | 0 | 0 |
| R3 | 0 | 0 |
| R4 | 4 | 0 |
| R6 | 1 | 0 |
| R7 | 3 | 1 |

6. Same-service history: Dev level equals QA level for 4 of 7 QA records; LR returned the QA level where the two differed in 2/3.

Records: 14 (7 services, SVC-089 to SVC-095; Dev and QA each). Recorded levels: 9 High, 4 Medium, 1 Low. Outcomes: 1 Failed, 9 Delayed, 4 Success.
Freeze: commit 14d6d1c (PROTOCOL.md + freeze_manifest.json), 2026-11-06 22:16 UTC; ratings requested afterwards. The stage-2 script's own output is external_check_table.md; this file adds the per-environment and per-rule counts from its JSON output.
