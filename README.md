# OCP-to-GKE migration risk prediction and mitigation recommendation

[![DOI](https://zenodo.org/badge/1442265979.svg)](https://doi.org/10.5281/zenodo.23869306)

Code, experiment manifests, result files, data dictionary and a synthetic example dataset for the paper

> Shommo G, Abdelgader AY. *Predicting Kubernetes Cloud Migration Risk from Enterprise OCP-to-GKE Records: A Machine-Learning and Mitigation Recommendation Framework.* Submitted to the Journal of Cloud Computing, 2026.

The study asks whether 13 attributes recorded at the planning stage of a service migration predict the risk level that engineers assigned after the migration (Low / Medium / High), compares Logistic Regression, Random Forest and XGBoost under repeated service-grouped cross-validation and on a reserved holdout, and links the prediction to eight inspectable mitigation rules. A bilingual (English / Arabic) decision-support prototype implements the pipeline, the models and the rules.

## What is in the repository

| Path | Content |
|---|---|
| `backend/` | FastAPI backend: data pipeline with integrity gate and audit log (`data/`), experiments (`experiments/`: service-grouped split, repeated StratifiedGroupKFold runner, seed study, nested tuning), model factory and registry (`models/`), exact additive attribution and permutation importance (`explain/`), deterministic rule engine R1-R8 (`recommend/rules.yaml`, `recommend/engine.py`), exports |
| `frontend/` | React single-page application (14 pages, English and Arabic); `frontend/dist/` is the built bundle served by the backend, so Node.js is not required to run the app |
| `data/results/` | Official result files behind the paper (aggregate only): cross-validation summaries, seed sensitivity, tuning study, holdout report and confusion matrix, permutation importance, run manifests |
| `data/example/` | Synthetic example workbook with the study schema (not real data) and its generator |
| `docs/DATA_DICTIONARY.md` | All 27 columns: type, value domain, timing (planning / execution / label), label codebook |
| `docs/CHANGELOG.md` | Development history of the application, including the protocol change that reserved the holdout before the official model comparison |
| `paper/` | The analysis and figure scripts used for the paper, with the results they produced |
| `tests/` | Pipeline integrity and oracle test, leakage guard on the feature sets, rule-engine consistency, API smoke tests; the historical-evidence tests run only on the real data |

The real dataset is **not** included (see `data/README.md`). Without it, the code runs on the synthetic example; results obtained on that file are not evidence of anything.

## Run

Python 3.11-3.13. The study used Python 3.13.16, scikit-learn 1.8.0, XGBoost 3.3.0 and pandas 3.0.2 (`paper/requirements-pinned.txt`); other versions run but may change Random Forest results slightly.

```bash
pip install -r requirements.txt
uvicorn backend.api.main:app --port 8000        # then open http://localhost:8000
# or: docker compose up --build
```

The application opens on the synthetic example and says so in its data banner. To use the real workbook under the organization's authorization, place it at `data/raw/OCP_GKE_Migration_Risk_Dataset_REAL_176.xlsx` or set `MRA_DATASET_XLSX`.

Official experiments (pool-only comparison, seed study, holdout evaluation) are driven from the application's *Live training* page or from `backend/experiments/runner.py`; the paper's additional analyses are in `paper/` (see `paper/README.md`).

```bash
pytest -q                                        # tests that do not need the real data
```

## How the holdout was handled

The reserved holdout is the seed-42 service-grouped split (18 services, 36 records) produced by `backend/experiments/split.py`. Sequence of events, as dated in the paper's Table A2: (1) an initial comparison round, the original tuning study and a feature screen used all 176 records; (2) the protocol was then changed to reserve the holdout, and every selection experiment was re-run on the 140-record pool; (3) the selected model (Logistic Regression) was evaluated once on the holdout on 11 July 2026; (4) the additional analyses of the November 2026 manuscript (`paper/r11_presubmission_analyses.py`) were run in October-November 2026 on the pool only, with the holdout result already known. The holdout services had taken part in step (1), so the holdout result is a post-selection check, not an independent confirmation; the application's interface and this changelog's older entries once described it as fully independent, and that wording was corrected in v46.3-public. The paper describes the history in Section 3.4 and its implications in Section 5.3.

## Blind external check (paper Section 4.9)

Seven services were added to the program after the research extract and were never part of any analysis. Their 14 records were used for a blind check of the released system: the protocol (`paper/external_check/PROTOCOL.md`) was written first; the serving models refit on the 176 records, the baselines and the rule engine were applied to the 13 planning attributes of the new records and the predictions were frozen with their SHA-256 and time in `paper/external_check/freeze_manifest.json`, committed (14d6d1c) before the ratings were requested; the ratings were then compared with the frozen predictions (`external_check_table.md`, committed as a443ea8). The scripts `stage1_freeze_predictions.py` and `stage2_compare.py` reproduce the procedure for any further set of unseen records.

## Citation and license

See `CITATION.cff`. Archived on Zenodo: https://doi.org/10.5281/zenodo.23869306 always resolves to the latest version (this release, v46.4-public, receives its own version DOI on Zenodo, cited in the paper); earlier versions: v46.3-public https://doi.org/10.5281/zenodo.23982143, v46.1-public https://doi.org/10.5281/zenodo.23871407 and v46-public https://doi.org/10.5281/zenodo.23869307. Code is released under the MIT License. The data dictionary and the synthetic example may be reused with attribution. The real migration records are not part of this release.
