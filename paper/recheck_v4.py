from pathlib import Path
import sys, json
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
from scipy import stats
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import f1_score
from backend.core import config as C
from backend.data.pipeline import run as run_pipeline
from backend.experiments.split import vault_carve
from backend.models.factory import make_model
CL=C.RISK_CLASSES; code={c:i for i,c in enumerate(CL)}
P,G,_=run_pipeline(save=False); tr,te=vault_carve(P,P.Risk_Level,G)
pool,gp=P.iloc[tr].reset_index(drop=True),G.iloc[tr].reset_index(drop=True)
def trig(r,E): return {"R1":E.Has_DB_Dependency==1,"R2":(E.Has_Network_Change==1)|(E.Firewall_Rules_Count>=5),
 "R3":E.Owner_Availability.isin(["Delayed","Unknown"]),"R4":(E.Has_Config_Change==1)&(E.Environment=="QA"),"R6":E.External_Integrations_Count>=3}[r]
pool["Rule_Score"]=sum(trig(r,pool).astype(int) for r in ["R1","R2","R3","R4","R6"])
y=pool.Risk_Level.map(code).astype(int)
def folds():
    for rep in range(5):
        for a,b in StratifiedGroupKFold(5,shuffle=True,random_state=42+rep).split(pool,y,gp): yield rep,a,b
def cvf(feats,name="Logistic Regression"):
    out=[];oof={}
    for rep,a,b in folds():
        m=make_model(name,feats); m.fit(pool[feats].iloc[a],y.iloc[a])
        pe=m.predict(pool[feats].iloc[b]); pr=m.predict_proba(pool[feats].iloc[b])
        out.append(f1_score([CL[i] for i in y.iloc[b]],[CL[i] for i in pe],average="macro",zero_division=0))
        if rep==0:
            hi=list(m.classes_).index(2)
            for k,ix in enumerate(b): oof[int(ix)]=(int(y.iloc[ix]),float(pr[k,hi]),int(pe[k]))
    return np.array(out),oof
F=C.PRE_EXEC_FEATURES
lr,oof_lr=cvf(F)
def nb(d): J=len(d); v=np.var(d,ddof=1); t=d.mean()/np.sqrt((1/J+28/112)*v); return round(float(2*stats.t.sf(abs(t),J-1)),4)
res={}
for lbl,ft in {"rule":["Rule_Score"],"cc":["Complexity_Level","Business_Criticality"],"c":["Complexity_Level"],"b":["Business_Criticality"],"p":["Previous_Issues_Count"]}.items():
    f,_=cvf(ft); d=lr-f; res[lbl]={"mean":round(d.mean(),4),"sd0":round(d.std(),4),"wins":int((d>0).sum()),"p":nb(d)}
rf,oof_rf=cvf(F,"Random Forest")
d=lr-rf; res["rf"]={"mean":round(d.mean(),4),"sd0":round(d.std(),4),"wins":int((d>0).sum()),"p":nb(d)}
# like-for-like OOF repeat 1: RF default predictions vs LR threshold 0.40
idx=sorted(oof_rf); yt=np.array([oof_rf[i][0] for i in idx]); rfp=np.array([oof_rf[i][2] for i in idx])
lrp=np.array([oof_lr[i][1] for i in idx])
def rp(flag): return round(float((flag&(yt==2)).sum()/(yt==2).sum()),3), round(float((flag&(yt==2)).sum()/flag.sum()),3)
res["oof_rf_default_High_recall_prec"]=rp(rfp==2)
res["oof_lr_thr040_recall_prec"]=rp(lrp>=0.40)
# Dev rows with fixed labels
dev=[];qa=[];copy=[]
devlab=dict(zip(gp[pool.Environment=="Dev"],pool.Risk_Level[pool.Environment=="Dev"]))
for rep,a,b in folds():
    m=make_model("Logistic Regression",F); m.fit(pool[F].iloc[a],y.iloc[a])
    pe=np.array([CL[i] for i in m.predict(pool[F].iloc[b])]); ytl=pool.Risk_Level.iloc[b].to_numpy(); env=pool.Environment.iloc[b].to_numpy(); sv=gp.iloc[b].to_numpy()
    q=env=="QA"
    dev.append(f1_score(ytl[~q],pe[~q],labels=CL,average="macro",zero_division=0))
    qa.append(f1_score(ytl[q],pe[q],labels=CL,average="macro",zero_division=0))
    copy.append(f1_score(ytl[q],[devlab[s] for s in sv[q]],labels=CL,average="macro",zero_division=0))
res["fixed_labels"]={"dev_lr":[round(np.mean(dev),4),round(np.std(dev),4)],"qa_lr":[round(np.mean(qa),5),round(np.std(qa),4)],"qa_copy":[round(np.mean(copy),4),round(np.std(copy),4)],
  "qa_wins":int((np.array(qa)>np.array(copy)).sum()),"qa_ties":int((np.array(qa)==np.array(copy)).sum())}
print(json.dumps(res,indent=1))
json.dump(res,open("recheck_v4.json","w"),indent=1)
