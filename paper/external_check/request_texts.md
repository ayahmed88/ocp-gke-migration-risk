# Data-request texts (Arabic and English) — keep the organization unnamed in any document

## Request 1 — planning attributes only (before the freeze)

**AR:** نحتاج، للخدمات الملحقة التي أُضيفت إلى البرنامج بعد المستخرج البحثي (نحو سبع خدمات)، سجلَي Dev وQA لكل خدمة بالأعمدة التالية فقط، مجهَّلة كما في المستخرج السابق: Migration_ID، Service_Code، Environment، Service_Category، Business_Criticality، Complexity_Level، Has_DB_Dependency، DB_Type، Has_Network_Change، Firewall_Rules_Count، External_Integrations_Count، Route_Ingress_Changed، Has_Config_Change، Owner_Availability، Previous_Issues_Count. من فضلكم **لا** ترسلوا في هذه المرحلة Risk_Level ولا Outcome ولا Recommended_Action ولا أي حقل من مرحلة التنفيذ؛ سنطلبها في رسالة لاحقة بعد تجميد تنبؤات النظام. ونرجو تأكيد نقطتين: (1) أن هذه الخدمات صُنّفت بالإجراء نفسه (المستوى يقترحه مهندس التنفيذ مع مالك المنتج ويعتمده قائد الفريق)، و(2) أن قيم التخطيط أُدخلت قبل الهجرة ولم تُعدَّل بعدها.

**EN:** For the services added to the program after the research extract (about seven), we need the Dev and the QA record of each service with these columns only, de-identified as in the earlier extract: Migration_ID, Service_Code, Environment, Service_Category, Business_Criticality, Complexity_Level, Has_DB_Dependency, DB_Type, Has_Network_Change, Firewall_Rules_Count, External_Integrations_Count, Route_Ingress_Changed, Has_Config_Change, Owner_Availability, Previous_Issues_Count. Please do **not** include Risk_Level, Outcome, Recommended_Action or any execution-phase field at this stage; we will request them separately after the system's predictions have been frozen. Please also confirm (1) that these services were rated by the same procedure (level proposed by the executing engineer with the product owner, approved by the team lead) and (2) that the planning values were entered before migration and not changed afterwards.

## Request 2 — ratings and outcomes (after the freeze is pushed)

**AR:** تم تجميد تنبؤات النظام للسجلات المرسلة (بصمة الملف وتاريخه مسجَّلان في المستودع العام). نرجو الآن إرسال الأعمدة التالية لنفس Migration_ID: Risk_Level، Outcome، Recommended_Action، وValidation_Result إن توفّر (وبقية حقول التنفيذ إن تيسّر).

**EN:** The system's predictions for the records you sent have been frozen (file hash and time are recorded in the public repository). Please now send, for the same Migration_IDs: Risk_Level, Outcome, Recommended_Action and, if available, Validation_Result (and the remaining execution-phase fields if convenient).
