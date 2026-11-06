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
   → `external_check_results.json` and `external_check_table.md` (aggregate counts only; these go into the paper).

Do not edit predictions_frozen.csv after step 2: stage 2 verifies its SHA-256 against the manifest and aborts on any change.
