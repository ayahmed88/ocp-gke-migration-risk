"""Data Dictionary service — the Phase-1 curated dictionary, computed live."""
import pandas as pd
from backend.core import config as C
from backend.data.pipeline import load_raw

MEANING = {
 "Migration_ID":"Anonymized record ID (MIG-001..176)","Service_Code":"Anonymized service ID; same code across a service's Dev/QA rows",
 "Environment":"Environment of the migration activity","Source_Platform":"Source platform (constant OCP)","Target_Platform":"Target platform (constant GKE)",
 "Service_Category":"Service type","Business_Criticality":"Business criticality of the service","Complexity_Level":"Migration complexity rating (1-5)",
 "Has_DB_Dependency":"Service depends on a database","DB_Type":"Database engine when dependency exists","Has_Network_Change":"Network change required",
 "Firewall_Rules_Count":"Firewall rules to create/modify","External_Integrations_Count":"Number of external integrations","Route_Ingress_Changed":"Route/Ingress definition changed",
 "Has_Config_Change":"Environment configuration change required","Owner_Availability":"Service owner availability","Previous_Issues_Count":"Issues recorded in prior activities",
 "Validation_Attempts":"Validation attempts performed","DB_Access_Issue":"DB access problem observed in execution","Network_Access_Issue":"Network access problem observed",
 "Image_Build_Issue":"Container image build problem observed","Validation_Result":"Post-migration validation result","Migration_Duration_Hours":"Duration of the activity (hours)",
 "Cutover_Delay_Days":"Cutover delay vs plan (days)","Outcome":"Final activity outcome","Risk_Level":"Expert-assigned migration risk","Recommended_Action":"Historical mitigation action(s)"}
ROLE = {"Migration_ID":"Identifier","Service_Code":"Identifier / grouping key","Source_Platform":"Constant (dropped)","Target_Platform":"Constant (dropped)",
        "Risk_Level":"TARGET (primary)","Outcome":"TARGET (secondary)","Recommended_Action":"Derived label (excluded)"}
STATIC = {"Service_Category":"Yes","Business_Criticality":"Yes","Has_DB_Dependency":"Yes","DB_Type":"Yes",
          "Source_Platform":"Yes (constant)","Target_Platform":"Yes (constant)","Complexity_Level":"Pending F2"}
ENC = {"DB_Type":"NaN→'None'; One-Hot","Service_Category":"One-Hot","Business_Criticality":"Ordinal L<M<H","Owner_Availability":"One-Hot",
       "Environment":"One-Hot","Validation_Result":"One-Hot (FULL only)","Migration_ID":"Excluded","Service_Code":"CV grouping key only",
       "Source_Platform":"Excluded","Target_Platform":"Excluded","Recommended_Action":"Excluded (leakage)"}

def build() -> list[dict]:
    df = load_raw(); out = []
    for c in df.columns:
        s = df[c]
        typ = "Numeric" if s.dtype.kind in "if" else "Categorical"
        typical = (f"{s.min()}–{s.max()}" if typ == "Numeric"
                   else ", ".join(map(str, s.dropna().unique()[:5])))
        pre = ("Yes" if c in C.PRE_EXEC_FEATURES else
               "No (execution)" if c in C.EXEC_PHASE_FEATURES else "n/a")
        leak = ("High — FULL set only" if c in C.EXEC_PHASE_FEATURES else
                "HIGH — never a feature" if c == "Recommended_Action" else
                "Low" if c in C.PRE_EXEC_FEATURES else "n/a")
        out.append({"column": c, "meaning": MEANING[c], "type": typ,
                    "typical": typical, "missing": int(s.isna().sum()),
                    "unique": int(s.nunique(dropna=True)),
                    "role": ROLE.get(c, "Feature"), "pre_exec": pre,
                    "leakage": leak, "encoding": ENC.get(c, "None (numeric)"),
                    "static_per_service": STATIC.get(c, "No (activity-level)")})
    return out
