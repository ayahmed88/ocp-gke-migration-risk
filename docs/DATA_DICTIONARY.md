# Data dictionary (27 columns, 176 records = 88 services x {Dev, QA})

Timing: **planning** = known or planned before the environment's migration started and fixed during execution (as confirmed by the author who prepared the dataset; the tracker keeps milestone dates but no field-level change history). **execution** = observed during or after the migration; never used as a predictor in the official experiments. **label** = target or derived field.

| # | Column | Type | Values (study data, n = 176) | Timing | Notes |
|---|---|---|---|---|---|
| 1 | Migration_ID | identifier | MIG-001 .. MIG-176 | - | de-identified record code; dropped before modelling |
| 2 | Service_Code | identifier | SVC-001 .. SVC-088 (each twice) | - | de-identified service code; used only as the grouping key (service-grouped splits) |
| 3 | Environment | nominal | Dev 88; QA 88 | planning | one-hot |
| 4 | Source_Platform | constant | OCP | - | dropped (constant) |
| 5 | Target_Platform | constant | GKE | - | dropped (constant) |
| 6 | Service_Category | nominal | Integration 56; API 34; Microservice 34; Web 30; Batch 22 | planning | one-hot |
| 7 | Business_Criticality | ordinal | Low 46; Medium 86; High 44 | planning | set jointly by the technical team and service owners during assessment |
| 8 | Complexity_Level | integer 1-5 | median 3 (IQR 2-4) | planning | set jointly by the technical team and service owners during assessment |
| 9 | Has_DB_Dependency | binary | 1 in 67.0% | planning | |
| 10 | DB_Type | nominal | SQLServer 46; MySQL 34; PostgreSQL 22; Oracle 16; empty 58 | planning | empty iff Has_DB_Dependency = 0; filled with the explicit category `None` in preprocessing |
| 11 | Has_Network_Change | binary | 1 in 68.2% | planning | |
| 12 | Firewall_Rules_Count | count 0-10 | median 3.5 (IQR 1-7) | planning | rules **planned** for the target environment, even if more were needed later |
| 13 | External_Integrations_Count | count 0-6 | median 3 (IQR 1-4) | planning | integrations **known before** migration, even if more were discovered later |
| 14 | Route_Ingress_Changed | binary | 1 in 51.1% | planning | change identified as required during assessment |
| 15 | Has_Config_Change | binary | 1 in 52.3% | planning | change identified as required during assessment |
| 16 | Owner_Availability | nominal | Available 130; Delayed 35; Unknown 11 | planning (timing uncertain) | set per environment before its migration; `Delayed` covers delays in response, testing or approval, and the exact moment of recording cannot be audited; the paper reports a sensitivity analysis without this attribute |
| 17 | Previous_Issues_Count | count 0-5 | median 2 (IQR 1-3) | planning | issues documented for that environment (Dev or QA) before its own migration; each environment has its own operational history, so the value differs between the Dev and QA records of 49 services; for a QA record it excludes problems met during the same service's Dev migration |
| 18 | Validation_Attempts | integer 1-4 | 1: 49; 2: 63; 3: 44; 4: 20 | execution | |
| 19 | DB_Access_Issue | binary | 1 in 31 | execution | |
| 20 | Network_Access_Issue | binary | 1 in 39 | execution | |
| 21 | Image_Build_Issue | binary | 1 in 30 | execution | used by rule R5 (execution-stage rule) |
| 22 | Validation_Result | nominal | Pass 88; Partial 62; Fail 26 | execution | |
| 23 | Migration_Duration_Hours | integer 9-39 | mean 22.4 | execution | |
| 24 | Cutover_Delay_Days | integer 0-7 | 0: 68; 1: 39; 2: 30; 3: 21; 4: 6; 5: 9; 7: 3 | execution | |
| 25 | Outcome | label (derived) | Success 68; Delayed 82; Failed 26 | execution | derived deterministically: Failed if Validation_Result = Fail; Delayed if Partial or Cutover_Delay_Days > 0; otherwise Success. `Failed` means the designated cutover attempt failed; every such migration succeeded at a second attempt after remediation |
| 26 | Risk_Level | label (primary target) | Low 15; Medium 68; High 93 | after migration | assigned by the responsible engineer after the migration using general severity criteria and the validation results, approved by the team lead; more than ten engineers took part; neither author took part |
| 27 | Recommended_Action | label (historical) | semicolon-separated phrases (8 distinct) | after migration | the historical guidance recorded for the migration; the rule engine (backend/recommend/rules.yaml, R1-R8) was derived from it and audited against it; never a predictor |

## Label codebook

**Risk_Level** (assigned after each migration by the responsible engineer using the program's general severity criteria and the validation results; approved by the team lead). The documented criteria describe:
- **Low**: a simple service with an available owner, low complexity, limited dependencies and successful validation.
- **Medium**: moderate complexity or dependency, partial validation, a minor delay or repeated validation attempts.
- **High**: high complexity, a database or network dependency, owner delay, multiple issues or failed validation.

The criteria combine planning attributes with validation results; expert judgement decides borderline cases. No mechanical rule reproduces the labels exactly, and the study treats the label as a retrospective expert assessment (paper, Section 3.2 and 5.3).

**Outcome**: Failed if Validation_Result = Fail; Delayed if Validation_Result = Partial or Cutover_Delay_Days > 0; otherwise Success (reproduces all 176 recorded values).

**Recommended_Action** phrases and the rule that reproduces each one: `validate db connectivity` (R1), `verify firewall/network rules` (R2), `confirm owner availability` (R3), `review environment-specific configuration` (R4), `review image build pipeline` (R5), `test external integrations` (R6), `schedule extended validation window` (R7), `standard validation and cutover checklist` (R8). Matching is a case-insensitive phrase search.
