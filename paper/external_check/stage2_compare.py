"""Stage 2 of the external check (paper/external_check/PROTOCOL.md): compare the frozen predictions with the ratings
and outcomes requested AFTER the freeze. Computes only the quantities of PROTOCOL.md Section 3.

Input: a workbook or CSV with Migration_ID, Risk_Level, Outcome, Recommended_Action (Validation_Result optional).
Run (from the repository root):
  python paper/external_check/stage2_compare.py path/to/new_services_labels.xlsx [--sheet NAME]
Writes paper/external_check/external_check_results.json and external_check_table.md.
"""
import sys, json, hashlib, argparse
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass
from pathlib import Path
HERE = Path(__file__).resolve().parent
import pandas as pd
from scipy.stats import beta

PHRASES = {"R1": "validate db connectivity", "R2": "verify firewall/network rules", "R3": "confirm owner availability",
           "R4": "review environment-specific configuration", "R5": "review image build pipeline",
           "R6": "test external integrations", "R7": "schedule extended validation window",
           "R8": "standard validation and cutover checklist"}
COMPARED_RULES = ["R1", "R2", "R3", "R4", "R6", "R7"]          # R5 not evaluable before execution; R8 is the fallback

def cp_interval(k, n, alpha=0.05):
    lo = 0.0 if k == 0 else beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else beta.ppf(1 - alpha / 2, k + 1, n - k)
    return [round(float(lo), 3), round(float(hi), 3)]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("labels"); ap.add_argument("--sheet", default=None); ap.add_argument("--id-map", default=None); a = ap.parse_args()
    man = json.loads((HERE / "freeze_manifest.json").read_text())
    pred_path = HERE / "predictions_frozen.csv"
    h = hashlib.sha256(pred_path.read_bytes()).hexdigest()
    if h != man["predictions_sha256"]:
        sys.exit("ABORT: predictions_frozen.csv does not match freeze_manifest.json (sha256 differs); the freeze is void.")
    print(f"manifest: frozen_at {man['frozen_at_utc']} | predictions sha256 {man['predictions_sha256'][:12]}... (must equal the manifest committed to the public repository)")
    pred = pd.read_csv(pred_path)
    lp = Path(a.labels)
    lab = pd.read_csv(lp) if lp.suffix.lower() == ".csv" else pd.read_excel(lp, sheet_name=a.sheet or 0)
    need = ["Migration_ID", "Risk_Level", "Outcome", "Recommended_Action"]
    missing = [c for c in need if c not in lab.columns]
    if missing:
        sys.exit(f"labels file is missing {missing}")
    # the labels file carries the tracker's original IDs; map them to the study IDs frozen in stage 1
    map_path = Path(a.id_map) if a.id_map else lp.with_name("id_mapping_private.csv")
    if not set(lab.Migration_ID) <= set(pred.Migration_ID):
        if not map_path.exists():
            sys.exit(f"labels use original IDs and {map_path} was not found; pass --id-map")
        mp = pd.read_csv(map_path).set_index("Original_Migration_ID").Migration_ID
        unmapped = sorted(set(lab.Migration_ID) - set(mp.index))
        if unmapped:
            sys.exit(f"labels contain IDs absent from the mapping: {unmapped}")
        lab = lab.assign(Migration_ID=lab.Migration_ID.map(mp))
    d = pred.merge(lab[need + (["Validation_Result"] if "Validation_Result" in lab.columns else [])], on="Migration_ID", how="left", validate="one_to_one")
    if d.Risk_Level.isna().any():
        sys.exit("ABORT: some frozen records have no rating in the labels file; every frozen record must be reported.")
    n = len(d); R = {"n_records": int(n), "n_services": int(d.Service_Code.nunique()), "frozen_at_utc": man["frozen_at_utc"],
                     "predictions_sha256": h, "git_commit_at_freeze": man.get("git_commit")}

    def agree(col):
        k = int((d[col] == d.Risk_Level).sum())
        per_env = {e: f"{int(((d[col] == d.Risk_Level) & (d.Environment == e)).sum())}/{int((d.Environment == e).sum())}" for e in ["Dev", "QA"]}
        return {"agree": k, "n": int(n), "ci95": cp_interval(k, n), "per_environment": per_env}
    def high_vs_rest(flag):
        rh = d.Risk_Level == "High"
        return {"recorded_High_flagged": f"{int((flag & rh).sum())}/{int(rh.sum())}",
                "recorded_nonHigh_not_flagged": f"{int((~flag & ~rh).sum())}/{int((~rh).sum())}"}

    # 1-3: primary, High-vs-rest, baselines, secondary models
    R["1_primary_LR13"] = agree("LR13_pred")
    R["2_high_vs_rest_LR13"] = high_vs_rest(d.LR13_pred == "High")
    R["3_baselines"] = {
        "LR_rulecount": {**agree("LR_rulecount_pred"), **high_vs_rest(d.LR_rulecount_pred == "High")},
        "flag_rule_ge3": high_vs_rest(d.flag_rule_ge3 == 1),
        "LR_criteria5": {**agree("LR_criteria5_pred"), **high_vs_rest(d.LR_criteria5_pred == "High")},
        "RF13_secondary": {**agree("RF13_pred"), **high_vs_rest(d.RF13_pred == "High")},
        "XGB13_secondary": {**agree("XGB13_pred"), **high_vs_rest(d.XGB13_pred == "High")},
    }
    # 4: outcomes
    R["4_outcomes"] = {}
    for oc in ["Failed", "Delayed"]:
        m = d.Outcome == oc
        R["4_outcomes"][oc] = {"n": int(m.sum()),
                               "LR13_predicted_High": int((m & (d.LR13_pred == "High")).sum()),
                               "rule_ge3_flagged": int((m & (d.flag_rule_ge3 == 1)).sum())}
    # 5: rule consistency (pre-execution rules and R7; R5 excluded; R8 fallback ignored)
    exact, dis = 0, {r: {"fired_not_recorded": 0, "recorded_not_fired": 0} for r in COMPARED_RULES}
    for _, row in d.iterrows():
        fired = {r for r in str(row.rules_fired_LR13).split(";") if r in COMPARED_RULES}
        rec_txt = str(row.Recommended_Action).lower()
        recorded = {r for r in COMPARED_RULES if PHRASES[r] in rec_txt}
        exact += int(fired == recorded)
        for r in COMPARED_RULES:
            if r in fired and r not in recorded: dis[r]["fired_not_recorded"] += 1
            if r in recorded and r not in fired: dis[r]["recorded_not_fired"] += 1
    R["5_rule_consistency"] = {"records_with_identical_sets": f"{exact}/{n}", "disagreements_by_rule": dis,
                               "note": "R5 not evaluable before execution; R8 fallback not compared"}
    # 6: same-service history
    dev = d[d.Environment == "Dev"].set_index("Service_Code").Risk_Level
    qa = d[d.Environment == "QA"].copy(); qa["Dev_label"] = qa.Service_Code.map(dev)
    qa = qa[qa.Dev_label.notna()]
    same = qa.Dev_label == qa.Risk_Level
    R["6_same_service_history"] = {"QA_records_with_Dev_record": int(len(qa)),
                                   "Dev_label_equals_QA_label": int(same.sum()),
                                   "LR13_correct_where_Dev_label_differs": f"{int(((~same) & (qa.LR13_pred == qa.Risk_Level)).sum())}/{int((~same).sum())}"}
    R["records"] = d[["Migration_ID", "Service_Code", "Environment", "Risk_Level", "LR13_pred", "LR13_pHigh", "Rule_Score",
                      "LR_rulecount_pred", "LR_criteria5_pred", "Outcome", "rules_fired_LR13"]].to_dict(orient="records")
    (HERE / "external_check_results.json").write_text(json.dumps(R, indent=2, default=str), encoding="utf-8")

    p = R["1_primary_LR13"]; b = R["3_baselines"]
    md = ["| Quantity | Value |", "|---|---|",
          f"| Records (services) | {n} ({R['n_services']}) |",
          f"| Frozen at (UTC) / commit | {man['frozen_at_utc']} / {man.get('git_commit')} |",
          f"| 1. LR13 agreement with recorded level | {p['agree']}/{n} (95% CI {p['ci95'][0]}-{p['ci95'][1]}); Dev {p['per_environment']['Dev']}, QA {p['per_environment']['QA']} |",
          f"| 2. LR13 High-vs-rest | recorded High flagged {R['2_high_vs_rest_LR13']['recorded_High_flagged']}; non-High not flagged {R['2_high_vs_rest_LR13']['recorded_nonHigh_not_flagged']} |",
          f"| 3. Rule-count LR agreement | {b['LR_rulecount']['agree']}/{n}; High flagged {b['LR_rulecount']['recorded_High_flagged']} |",
          f"| 3. Rule >= 3 flag | High flagged {b['flag_rule_ge3']['recorded_High_flagged']}; non-High not flagged {b['flag_rule_ge3']['recorded_nonHigh_not_flagged']} |",
          f"| 3. Criteria-only LR agreement | {b['LR_criteria5']['agree']}/{n} |",
          f"| 3. RF / XGBoost agreement (secondary) | {b['RF13_secondary']['agree']}/{n} / {b['XGB13_secondary']['agree']}/{n} |",
          f"| 4. Failed first attempts predicted High (LR13 / rule >= 3) | {R['4_outcomes']['Failed']['LR13_predicted_High']} / {R['4_outcomes']['Failed']['rule_ge3_flagged']} of {R['4_outcomes']['Failed']['n']} |",
          f"| 4. Delayed predicted High (LR13 / rule >= 3) | {R['4_outcomes']['Delayed']['LR13_predicted_High']} / {R['4_outcomes']['Delayed']['rule_ge3_flagged']} of {R['4_outcomes']['Delayed']['n']} |",
          f"| 5. Rule set identical to recorded actions | {R['5_rule_consistency']['records_with_identical_sets']} |",
          f"| 6. Dev label equals QA label | {R['6_same_service_history']['Dev_label_equals_QA_label']}/{R['6_same_service_history']['QA_records_with_Dev_record']}; LR13 correct where they differ {R['6_same_service_history']['LR13_correct_where_Dev_label_differs']} |"]
    (HERE / "external_check_table.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))

if __name__ == "__main__":
    main()
