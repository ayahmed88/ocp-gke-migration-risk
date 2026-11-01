import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { PageIntro } from '../lib/ui'
import { useViewMode } from '../lib/viewMode'
import { get, post } from '../lib/api'
import { fieldLabel } from './Xai'

const NUM = { Complexity_Level: [1, 5], Firewall_Rules_Count: [0, 10],
  External_Integrations_Count: [0, 6], Previous_Issues_Count: [0, 5] }
const BIN = ['Has_DB_Dependency', 'Has_Network_Change', 'Route_Ingress_Changed', 'Has_Config_Change']
const CAT = ['Environment', 'Service_Category', 'Business_Criticality', 'DB_Type', 'Owner_Availability']
const ORDER = ['Environment', 'Service_Category', 'Business_Criticality', 'Complexity_Level',
  'Has_DB_Dependency', 'DB_Type', 'Has_Network_Change', 'Firewall_Rules_Count',
  'External_Integrations_Count', 'Route_Ingress_Changed', 'Has_Config_Change',
  'Owner_Availability', 'Previous_Issues_Count']
const RISK_COLORS = { Low: 'var(--risk-low)', Medium: 'var(--risk-medium)', High: 'var(--risk-high)' }

function Meter({ probs }) {
  // needle position = probability-weighted position across the three bands
  const order = ['Low', 'Medium', 'High']
  const centers = { Low: 1 / 6, Medium: 3 / 6, High: 5 / 6 }
  const pos = order.reduce((a, c) => a + (probs[c] || 0) * centers[c], 0) * 100
  return (
    <div style={{ padding: '14px 6px 4px' }}>
      <div className="meter">
        {order.map(c => <div key={c} className="band" style={{ width: '33.33%', background: RISK_COLORS[c], opacity: .8 }} />)}
        <div className="needle" style={{ insetInlineStart: `calc(${pos}% - 1.5px)` }} />
      </div>
    </div>
  )
}

export default function Predict({ go }) {
  const { t, i18n } = useTranslation()
  const vm = useViewMode()
  const [whyAll, setWhyAll] = useState(false)
  const [models, setModels] = useState(null)
  const [domains, setDomains] = useState(null)
  const [modelId, setModelId] = useState('')
  const [f, setF] = useState({ Environment: 'Dev', Service_Category: 'API', Business_Criticality: 'Medium',
    Complexity_Level: 3, Has_DB_Dependency: 0, DB_Type: 'None', Has_Network_Change: 0,
    Firewall_Rules_Count: 0, External_Integrations_Count: 0, Route_Ingress_Changed: 0,
    Has_Config_Change: 0, Owner_Availability: 'Available', Previous_Issues_Count: 0 })
  const [res, setRes] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)

  const loadModels = () => get('/api/models').then(d => {
    const all = d.models.filter(m => m.config === 'A_Risk_PRE-EXEC')
    const latestOf = a => all.filter(m => m.algorithm === a).slice(-1)[0]
    const serving = ['Logistic Regression', 'Random Forest', 'XGBoost'].map(latestOf).filter(Boolean)
    setModels(serving)
    if (serving.length && !modelId) setModelId(serving[0].model_id)
  })
  useEffect(() => { loadModels(); get('/api/dataset/summary').then(s => setDomains(s.categorical_domains)) }, [])

  const set = (k, v) => setF(o => ({ ...o, [k]: v }))
  const trainFirst = () => { go && go('training') }
  const submit = async () => {
    setBusy(true); setErr(null); setRes(null)
    const feats = { ...f }
    if (Number(feats.Has_DB_Dependency) === 0) feats.DB_Type = 'None'
    try { setRes(await post('/api/predict', { model_id: modelId, features: feats })) }
    catch (e) { setErr(e.message) } finally { setBusy(false) }
  }

  if (models && models.length === 0) return (<>
    <h2>{t('pred.title')}</h2>
      <PageIntro k="predict" />
    <div className="banner err" style={{ marginBottom: 14 }}>{t('pred.needModels')}</div>
    <button className="btn" onClick={trainFirst} disabled={busy}>{busy ? t('common.loading') : t('pred.trainNow')}</button>
  </>)

  return (
    <>
      <h2>{t('pred.title')}</h2>
      <p className="sub">{t('train.desc')}</p>
      <div className="card" style={{ marginBottom: 14 }}>
        <div className="field" style={{ maxWidth: 420, marginBottom: 16 }}>
          <label>{t('pred.model')}</label>
          <select value={modelId} onChange={e => setModelId(e.target.value)}>
            {(models || []).map(m => <option key={m.model_id} value={m.model_id}>{m.algorithm} {m.algorithm === 'Logistic Regression' ? t('pred.tagPrimary') : m.algorithm === 'Random Forest' ? '· ' + t('pred.tagRF') : '· ' + t('pred.tagXGB')}</option>)}
          </select>
        </div>
        <div className="formgrid">
          {ORDER.map(k => (
            <div className="field" key={k}>
              <label>{t('pred.fields.' + k)}</label>
              {CAT.includes(k) ? (
                <select value={f[k]} onChange={e => set(k, e.target.value)}
                        disabled={k === 'DB_Type' && Number(f.Has_DB_Dependency) === 0}>
                  {((domains && domains[k]) || [f[k]]).map(v => <option key={v}>{v}</option>)}
                </select>
              ) : BIN.includes(k) ? (
                <div className="seg">
                  <button type="button" className={Number(f[k]) === 1 ? 'on' : ''} onClick={() => set(k, 1)}>{t('pred.yes')}</button>
                  <button type="button" className={Number(f[k]) === 0 ? 'on' : ''} onClick={() => set(k, 0)}>{t('pred.no')}</button>
                </div>
              ) : (
                <input type="number" min={NUM[k][0]} max={NUM[k][1]} value={f[k]}
                       onChange={e => set(k, e.target.value === '' ? '' : Number(e.target.value))} />
              )}
            </div>
          ))}
        </div>
        <div style={{ marginTop: 18 }}>
          <button className="btn" onClick={submit} disabled={busy || !modelId}>
            {busy ? t('common.loading') : t('pred.submit')}
          </button>
        </div>
        {err && <div className="banner err" style={{ marginTop: 12 }}>{err}</div>}
      </div>

      {res && (
        <div className="card">
          <h3>{t('pred.resultTitle')}</h3>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, flexWrap: 'wrap' }}>
            <span className="stat" style={{ color: RISK_COLORS[res.prediction],
                fontSize: vm === 'present' ? 44 : undefined, fontWeight: vm === 'present' ? 800 : undefined,
                textShadow: vm === 'present' ? '0 0 26px var(--accent-glow)' : undefined }}>
                {t('risk.' + res.prediction)}</span>
              {vm === 'present' && <span className="mono" style={{ fontSize: 22, marginInlineStart: 12, color: 'var(--ink-2)' }}>
                {(100 * res.probabilities[res.prediction]).toFixed(1)}%</span>}
            <span className="muted mono" style={{ fontSize: 12.5 }}>{res.model.algorithm} · {res.model.model_id.slice(-8)}</span>
          </div>
          <h3 style={{ marginTop: 16 }}>{t('pred.meter')}</h3>
          <Meter probs={res.probabilities} />
          <h3 style={{ marginTop: 16 }}>{t('pred.probs')}</h3>
          {['High', 'Medium', 'Low'].map(c => (
            <div className="bar" key={c}>
              <span className="lbl">{t('risk.' + c)}</span>
              <div className="track"><div className="fill" style={{ width: (100 * res.probabilities[c]) + '%', background: RISK_COLORS[c] }} /></div>
              <span className="val">{(100 * res.probabilities[c]).toFixed(1)}%</span>
            </div>
          ))}
          {res.explanation && (() => {
            const items = res.explanation.contributions.slice(0, vm === 'present' && !whyAll ? 3 : 7)
            const max = Math.max(...items.map(i => Math.abs(i.contribution)), 1e-9)
            return (
              <>
                <h3 style={{ marginTop: 16 }}>{t('pred.why')}</h3>
                {items.map(i => (
                  <div className="bar" key={i.label}>
                    <span className="lbl" style={{ width: 210, fontSize: 12.5 }}>{fieldLabel(t, i.label)}</span>
                    <div className="track"><div className="fill" style={{ width: (100 * Math.abs(i.contribution) / max) + '%',
                      background: i.contribution > 0 ? RISK_COLORS[res.prediction] : 'var(--ink-2)' }} /></div>
                    <span className="val">{i.contribution > 0 ? '+' : ''}{i.contribution.toFixed(2)}</span>
                  </div>))}
                {vm === 'present' && res.explanation.contributions.length > 3 && (
                  <button className="btn ghost" style={{ marginTop: 6, fontSize: 12, padding: '4px 12px' }}
                    onClick={() => setWhyAll(a => !a)}>{whyAll ? t('pred.whyLess') : t('pred.whyMore')}</button>)}
                <p className="muted" style={{ fontSize: 12 }}>{t('pred.whyNote')}</p>
              </>
            )
          })()}
          {res.recommendations && (
            <>
              <h3 style={{ marginTop: 18 }}>{t('rec.predTitle')}</h3>
              {res.recommendations.recommendations.map(r => (
                <div key={r.rule_id} style={{ display: 'flex', gap: 10, alignItems: 'baseline', padding: '7px 0',
                     borderBottom: '1px solid var(--line)', flexWrap: 'wrap' }}>
                  <span className="chip" style={{ color: { high: 'var(--risk-high)', medium: 'var(--risk-medium)', low: 'var(--ink-2)' }[r.priority] }}>
                    <span className="dot" />{r.rule_id}</span>
                  <b style={{ fontSize: 13.5 }}>{t('rec.actions.' + r.action + '.name')}</b>
                  <span className="mono muted" style={{ fontSize: 11.5 }}>{t('rec.because')}: {r.triggered_by}</span>
                </div>))}
              {res.recommendations.not_evaluable_at_this_stage.length > 0 && (
                <p className="muted" style={{ fontSize: 11.5, marginTop: 8 }}>
                  {t('rec.notEval')} {res.recommendations.not_evaluable_at_this_stage.map(r => r.rule_id).join('، ')}</p>)}
              <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>⚖️ {t('rec.gov')}</p>
            </>
          )}
          <p className="muted" style={{ fontSize: 12.5, marginTop: 14 }}>⚖️ {t('pred.disclaimer')}</p>
        </div>
      )}
    </>
  )
}
