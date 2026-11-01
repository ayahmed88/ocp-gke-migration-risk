from pathlib import Path
import sys, json
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import f1_score
from backend.core import config as C
from backend.data.pipeline import run as run_pipeline
from backend.experiments.split import vault_carve
from backend.models.factory import make_model
CL=C.RISK_CLASSES; code={c:i for i,c in enumerate(CL)}
P,G,_=run_pipeline(save=False); tr,te=vault_carve(P,P.Risk_Level,G)
pool,gp=P.iloc[tr].reset_index(drop=True),G.iloc[tr].reset_index(drop=True)
hold,gh=P.iloc[te].reset_index(drop=True),G.iloc[te].reset_index(drop=True)
F=C.PRE_EXEC_FEATURES; y=pool.Risk_Level.map(code).astype(int)
# per-fold: LR on QA test rows vs Dev-label copy on the same QA rows (Dev label of same service)
devlab = dict(zip(gp[pool.Environment=="Dev"], pool.Risk_Level[pool.Environment=="Dev"]))
lr_qa, copy_qa, lr_dev = [], [], []
for rep in range(5):
    for a,b in StratifiedGroupKFold(5,shuffle=True,random_state=42+rep).split(pool[F],y,gp):
        m=make_model("Logistic Regression",F); m.fit(pool[F].iloc[a],y.iloc[a])
        pe=np.array([CL[i] for i in m.predict(pool[F].iloc[b])]); yt=pool.Risk_Level.iloc[b].to_numpy()
        env=pool.Environment.iloc[b].to_numpy(); svc=gp.iloc[b].to_numpy()
        q=env=="QA"; d=env=="Dev"
        lr_qa.append(f1_score(yt[q],pe[q],average="macro",zero_division=0))
        lr_dev.append(f1_score(yt[d],pe[d],average="macro",zero_division=0))
        copy_qa.append(f1_score(yt[q],[devlab[s] for s in svc[q]],average="macro",zero_division=0))
m=make_model("Logistic Regression",F); m.fit(pool[F],y)
pe=np.array([CL[i] for i in m.predict(hold[F])]); yt=hold.Risk_Level.to_numpy(); q=hold.Environment.to_numpy()=="QA"
hd=dict(zip(gh[hold.Environment=="Dev"],hold.Risk_Level[hold.Environment=="Dev"]))
out={"cv_QA_rows":{"LR13":[round(np.mean(lr_qa),4),round(np.std(lr_qa),4)],"DevLabelCopy":[round(np.mean(copy_qa),4),round(np.std(copy_qa),4)],
      "LR_wins_of_25":int((np.array(lr_qa)>np.array(copy_qa)).sum())},
     "cv_Dev_rows_LR13":[round(np.mean(lr_dev),4),round(np.std(lr_dev),4)],
     "holdout_QA_rows":{"LR13":round(f1_score(yt[q],pe[q],average="macro",zero_division=0),4),
       "DevLabelCopy":round(f1_score(yt[q],[hd[s] for s in gh[q]],average="macro",zero_division=0),4)},
     "holdout_Dev_rows_LR13":round(f1_score(yt[~q],pe[~q],average="macro",zero_division=0),4)}
print(json.dumps(out,indent=1))
R=json.load(open("reviewer_analyses.json")); R["B2b_QA_rows_LR_vs_DevCopy"]=out; json.dump(R,open("reviewer_analyses.json","w"),indent=1)
