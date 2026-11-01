from pathlib import Path
import sys, json
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from scipy import stats
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import f1_score, roc_auc_score, accuracy_score
from sklearn.utils.class_weight import compute_sample_weight
from backend.core import config as C
from backend.data.pipeline import run as run_pipeline
from backend.experiments.split import vault_carve
from backend.models.factory import make_model, needs_sample_weight
CL=C.RISK_CLASSES; code={c:i for i,c in enumerate(CL)}
P,G,_=run_pipeline(save=False); tr,te=vault_carve(P,P.Risk_Level,G)
pool,gp=P.iloc[tr].reset_index(drop=True),G.iloc[tr].reset_index(drop=True)
hold=P.iloc[te].reset_index(drop=True)
y=pool.Risk_Level.map(code).astype(int)
F13=C.PRE_EXEC_FEATURES; F12=[f for f in F13 if f!="Owner_Availability"]
def cv(name,feats):
    f1s=[];aucs=[]
    for rep in range(5):
        for a,b in StratifiedGroupKFold(5,shuffle=True,random_state=42+rep).split(pool,y,gp):
            m=make_model(name,feats); kw={"clf__sample_weight":compute_sample_weight("balanced",y.iloc[a])} if needs_sample_weight(name) else {}
            m.fit(pool[feats].iloc[a],y.iloc[a],**kw)
            pe=m.predict(pool[feats].iloc[b]); raw=m.predict_proba(pool[feats].iloc[b]); pr=np.zeros((len(b),3))
            for j,c in enumerate(m.classes_): pr[:,int(c)]=raw[:,j]
            f1s.append(f1_score([CL[i] for i in y.iloc[b]],[CL[i] for i in pe],average="macro",zero_division=0))
            aucs.append(roc_auc_score(y.iloc[b],pr,multi_class="ovr",average="macro",labels=[0,1,2]))
    return np.array(f1s),np.array(aucs)
def nb(d): J=len(d); v=np.var(d,ddof=1); t=d.mean()/np.sqrt((1/J+28/112)*v); return float(2*stats.t.sf(abs(t),J-1))
out={}
for name in ["Logistic Regression","Random Forest","XGBoost"]:
    f13,a13=cv(name,F13); f12,a12=cv(name,F12); d=f13-f12
    out[name]={"f1_13":[round(f13.mean(),4),round(f13.std(),4)],"f1_12":[round(f12.mean(),4),round(f12.std(),4)],
               "auc_13":round(a13.mean(),4),"auc_12":round(a12.mean(),4),
               "diff13_minus12":[round(d.mean(),4),round(d.std(),4)],"folds_13_ahead":int((d>0).sum()),"p":round(nb(d),4)}
assert out["Logistic Regression"]["f1_13"][0]==0.634
# holdout sensitivity (LR, 12 features) -- reported only as sensitivity, not as a new test
m=make_model("Logistic Regression",F12); m.fit(pool[F12],y)
yt=hold.Risk_Level.map(code).astype(int); pe=m.predict(hold[F12])
out["LR12_holdout_macroF1"]=round(f1_score([CL[i] for i in yt],[CL[i] for i in pe],average="macro",zero_division=0),4)
out["LR12_holdout_correct"]=int((yt.to_numpy()==pe).sum())
print(json.dumps(out,indent=1)); json.dump(out,open("owner_sensitivity.json","w"),indent=1)
