# Data

## What is here
- `example/SYNTHETIC_Example_Dataset_176.xlsx`: a **synthetic** workbook with the same 27 columns, 88 services x Dev/QA = 176 rows and the same value domains as the study dataset. It exists so that the pipeline, the experiments and the application run end to end. Its numbers are meaningless as evidence and do not reproduce the paper.
- `example/make_synthetic.py`: the generator (part of the repository build script).
- `results/`: the official result files behind the paper (cross-validation summaries, seed study, tuning study, holdout report with its confusion matrix, permutation importance, run manifests). They are aggregate; they contain no record-level data.
- `exports/`: figures and summary tables exported by the application from `results/`.
- `results/influential11_sensitivity.json`: an exploratory full-data (176-record) run from before the holdout was reserved, comparing the 13 planning attributes with an 11-attribute subset; it is superseded and is not reported in the paper. Its 13-attribute values (LR 0.608, RF 0.595, XGBoost 0.599) are the figures of the initial full-data comparison that the paper's Section 3.4 discloses.
- `../docs/CHANGELOG.md` is the development history as written at the time; entries up to v34 describe the holdout in the language then used ("sealed", "fully independent"). The paper's Section 3.4 gives the precise history, which supersedes that wording.

## What is not here
The real dataset (`raw/OCP_GKE_Migration_Risk_Dataset_REAL_176.xlsx`, 176 de-identified migration records) belongs to the source organization, which authorized its use for research and publication but not the public release of the record-level file; it is therefore not distributed. The same applies to `processed/` and to record-level predictions. Requests for access are assessed against the organization's authorization; contact the corresponding author.

## Using the real file
Place it at `data/raw/OCP_GKE_Migration_Risk_Dataset_REAL_176.xlsx`, or set `MRA_DATASET_XLSX=/path/to/file.xlsx`. The integrity gate (176 x 27, 88 services x 2 environments, unique identifiers, structural DB_Type missingness) and the verification against the workbook's CLEANED sheet then run exactly as in the study.
