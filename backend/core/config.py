"""Central configuration — single source of truth for the experiment design.

Every methodological constant lives here so that the thesis text, the app UI,
and the code can never drift apart.
"""
from pathlib import Path

# ---------------------------------------------------------------- paths ----
ROOT = Path(__file__).resolve().parents[2]
APP_VERSION = (ROOT / "VERSION").read_text().strip() if (ROOT / "VERSION").exists() else "dev"
import os
# Public release: the real workbook is not distributed. Point MRA_DATASET_XLSX at the real file when you have it;
# otherwise the synthetic example (same schema, random values) is used so the pipeline and the app can run.
RAW_XLSX = Path(os.environ["MRA_DATASET_XLSX"]) if os.environ.get("MRA_DATASET_XLSX") else (
    ROOT / "data" / "raw" / "OCP_GKE_Migration_Risk_Dataset_REAL_176.xlsx"
    if (ROOT / "data" / "raw" / "OCP_GKE_Migration_Risk_Dataset_REAL_176.xlsx").exists()
    else ROOT / "data" / "example" / "SYNTHETIC_Example_Dataset_176.xlsx")
IS_SYNTHETIC_DATA = RAW_XLSX.name.startswith("SYNTHETIC")
RAW_SHEET = "RAW_Dataset_176"
CLEANED_REF_SHEET = "CLEANED_Dataset_176"          # human-made reference, used as a verification oracle
PROCESSED_DIR = ROOT / "data" / "processed"
ARTIFACTS_DIR = ROOT / "data" / "artifacts"
RESULTS_DIR = ROOT / "data" / "results"

# ------------------------------------------------------- reproducibility ----
import os
SEED = int(os.environ.get("APP_SEED", 42))   # fixed & pre-declared; overridable via APP_SEED env
CV_N_SPLITS = 5                 # StratifiedGroupKFold folds
CV_N_REPEATS = 5                # repeats with seeds SEED..SEED+4  -> 25 folds

# ------------------------------------------------------------- columns ----
ID_COLS = ["Migration_ID", "Service_Code"]
CONSTANT_COLS = ["Source_Platform", "Target_Platform"]
GROUP_COL = "Service_Code"      # grouping key: both env rows of a service stay on the same CV side

TARGET_PRIMARY = "Risk_Level"                     # Low / Medium / High (expert-assigned)
TARGET_SECONDARY = "Outcome"                      # Success / Delayed / Failed
DERIVED_LABEL = "Recommended_Action"              # historical actions — NEVER a feature (leakage)

RISK_CLASSES = ["Low", "Medium", "High"]
OUTCOME_CLASSES = ["Success", "Delayed", "Failed"]

# 13 features available BEFORE execution — headline experiments (research objective:
# predict risk before execution). Verified against the workbook's Feature_Analysis sheet.
PRE_EXEC_FEATURES = [
    "Environment", "Service_Category", "Business_Criticality", "Complexity_Level",
    "Has_DB_Dependency", "DB_Type", "Has_Network_Change", "Firewall_Rules_Count",
    "External_Integrations_Count", "Route_Ingress_Changed", "Has_Config_Change",
    "Owner_Availability", "Previous_Issues_Count",
]
# +7 execution-phase signals -> 20 features. Secondary analysis only.
EXEC_PHASE_FEATURES = [
    "Validation_Attempts", "DB_Access_Issue", "Network_Access_Issue",
    "Image_Build_Issue", "Validation_Result", "Migration_Duration_Hours",
    "Cutover_Delay_Days",
]
FULL_FEATURES = PRE_EXEC_FEATURES + EXEC_PHASE_FEATURES

# ------------------------------------------------------------ encoding ----
ORDINAL_MAPS = {"Business_Criticality": ["Low", "Medium", "High"]}
NOMINAL_COLS = ["Environment", "Service_Category", "DB_Type",
                "Owner_Availability", "Validation_Result"]
DB_TYPE_FILL = "None"           # structural NaN (no DB dependency) -> explicit category

# Findings adopted with the author's approval (Phase 1):
# F3: Outcome is 100% rule-determined by execution fields -> predict Outcome from PRE-EXEC only.
# F4: class imbalance handled by class_weight='balanced' (no SMOTE).
# F5: always ingest RAW; cleaning is performed by this code with an audit trail.
