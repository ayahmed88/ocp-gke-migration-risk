# External check on services added after the research extract

Read PROTOCOL.md first. Order of operations (on the machine that holds the real 176-record workbook):

1. Request 1 to the program: the 13 planning attributes only (see request_texts.md). Save the file, e.g. `~/extcheck/new_services.xlsx`.
2. From the repository root:
   `python paper/external_check/stage1_freeze_predictions.py ~/extcheck/new_services.xlsx --sheet NEW_Services`
   (the script stops if the file carries Risk_Level, Outcome, Recommended_Action or any execution-phase column).
   It assigns study identifiers MIG-X01.. to the new records (the tracker's own numbers repeat numbers used in the 176-record
   extract) and writes `id_mapping_private.csv` next to the input file: keep it, never commit it; stage 2 reads it.
3. Commit and push `paper/external_check/PROTOCOL.md` and `paper/external_check/freeze_manifest.json`
   (not the input file; `predictions_frozen.csv` only if the data-sharing conditions allow). The push time is the public freeze time.
4. Request 2 to the program: Risk_Level, Outcome, Recommended_Action (and Validation_Result if available) for the same Migration_IDs.
5. `python paper/external_check/stage2_compare.py ~/extcheck/new_services_labels.xlsx`
   → `external_check_table.md` (aggregate counts; this is what the paper reports) and `external_check_results.json`,
   whose `records` section holds record-level values (ratings, predictions, outcomes per record): keep the JSON private
   unless the data-sharing conditions allow its release; only the table is committed.

Do not edit predictions_frozen.csv after step 2: stage 2 verifies its SHA-256 against the manifest and aborts on any change.

Environment note: the freeze of 6 November 2026 ran from the extracted v46.4-public package (no git checkout, hence
`git_commit: null` in the manifest) under Python 3.14.6 with the pinned libraries (scikit-learn 1.8.0, xgboost 3.3.0,
pandas 3.0.2); the study's main analyses use Python 3.13 (paper/requirements-pinned.txt). The model, rule and pipeline
code is identical in v46.3-public and v46.4-public.
Protocol note (7 November 2026, PROTOCOL.md itself unchanged): item 3 of the protocol reads "same quantities as 1 and 2" while
its closing sentence allows no interval other than item 1's; the stage-2 script computes a Clopper-Pearson interval for every
model as a by-product, and the paper reports only the pre-specified one (Table 10). The intervals for the other models in
external_check_table_full.md are therefore not pre-specified.
