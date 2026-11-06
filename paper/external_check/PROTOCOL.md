# External check on services added to the program after the research extract — pre-specified protocol

Version 1.0, 6 November 2026. This file is frozen (its SHA-256 is recorded in `freeze_manifest.json`) before any
label of the new services is requested or seen by either author.

## 1. What is being checked

The research dataset contains the complete in-scope cohort of 88 services (176 Dev and QA records) as it stood when
the extract was taken. A small number of further services (about seven) were added to the program later: they were
originally expected to remain on the source platform, were subsequently directed to migrate, and were migrated and
rated by the same procedure as the cohort (level proposed by the executing engineer with the product owner, approved by
the team lead). They were never part of any analysis, fold, tuning run or holdout, and neither author has seen their
ratings or outcomes.

This check asks one question: **when the serving models and rules released with the paper are applied to records they
have never seen, how often do they return the rating and the checks that the program recorded?** It is an external
check of the released system on unseen records from the same program. It is not an evaluation: the number of records
is far too small for a precise estimate, and the services are not a random sample of anything (they are the services
whose scope decision changed).

## 2. Blinding and sequence

1. **Request 1 (planning attributes only).** The authors request, for each new service and for both environments, the
   identifiers used in the research extract (Migration_ID, Service_Code, de-identified as before) and the 13
   planning-stage attributes of Table 1 — nothing else. The request explicitly excludes Risk_Level, Outcome,
   Recommended_Action, Validation_Result and every execution-phase field.
2. **Freeze.** `stage1_freeze_predictions.py` refuses any input file that contains a label or execution-phase column.
   It refits the serving models on the 176 research records exactly as the application's registry does, applies them
   and the rule engine to the new records, and writes `predictions_frozen.csv` and `freeze_manifest.json` (UTC time,
   SHA-256 of the input file, of the predictions file, of the 176-record workbook and of this protocol, software
   versions, repository version). The manifest (which carries the SHA-256 of the predictions file) is committed to the public repository before
   step 3, so the freeze time is publicly verifiable; the predictions file itself is record-level derived data and is
   published only if the data-sharing conditions allow, otherwise it is kept by the authors and verified by its hash.
3. **Request 2 (labels and outcomes).** Only after the freeze is public do the authors request Risk_Level, Outcome,
   Recommended_Action and, if available, Validation_Result for the same records.
4. **Compare.** `stage2_compare.py` checks the SHA-256 of `predictions_frozen.csv` against the manifest and computes
   only the quantities listed in Section 3. No model is refitted, no threshold is changed, no record is excluded.

## 3. Pre-specified quantities (all reported, in this order)

Let n be the number of new records (expected 14: seven services × Dev and QA).

1. **Primary.** Number of records whose recorded Risk_Level equals the level predicted by the serving Logistic
   Regression (LR, 13 attributes), k of n, with a Clopper–Pearson 95% interval. Also reported per environment.
2. **High-versus-rest.** For LR: recorded-High records predicted High (sensitivity count), recorded-non-High records
   predicted non-High (specificity count).
3. **Baselines, same quantities as 1 and 2:** LR on the rule-trigger count (the Table 5 baseline), the flag
   "rule-trigger count ≥ 3" (the Table 7 policy), and the criteria-only LR (five planning attributes). Random Forest
   and XGBoost are reported as secondary serving models.
4. **Outcomes.** Among records with Outcome = Failed, how many LR predicted High; the same for the rule ≥ 3 flag.
   Among records with Outcome = Delayed, the same two counts.
5. **Rule consistency.** For each record, the pre-execution rules fired (R1, R2, R3, R4, R6; R7 if the prediction is
   High) against the phrases in Recommended_Action; the number of records on which the fired set equals the recorded
   set, and the number of rule-level disagreements by rule. R5 is not evaluable before execution and is excluded.
6. **Same-service history.** For QA records, whether the recorded Dev level of the same service equals the recorded
   QA level (count), and whether the LR prediction for QA equals the recorded QA level when the Dev level does not.

No p-value, no interval other than the Clopper–Pearson interval in item 1, and no comparison beyond those listed.

## 4. Reporting commitment

Every quantity in Section 3 is reported in the paper whatever its value, in a short subsection of the Results (or an
appendix) headed as an external check on services added after the extract, with the freeze time, the repository
commit, and the statement that the ratings were requested only after the predictions had been frozen. The abstract and
conclusion may state the primary count in one clause. The check does not change any number in Sections 4.1 to 4.7.

## 5. What this check cannot show

It cannot estimate accuracy with useful precision (with n = 14, a count of 10 agreements has an interval of roughly
0.42 to 0.92). It does not evaluate the prototype with users and says nothing about the reliability of the rating
itself. It shows whether the released system, applied blind, reproduced the program's recorded ratings and checks on
records it had never seen.
