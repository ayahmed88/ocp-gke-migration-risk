import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { PageIntro } from '../lib/ui'
import { useViewMode } from '../lib/viewMode'
import { get } from '../lib/api'

const RISK_COLORS = { Low: 'var(--risk-low)', Medium: 'var(--risk-medium)', High: 'var(--risk-high)' }
export const fieldLabel = (t, label) => {
  if (label.includes(' = ')) {
    const [b, v] = label.split(' = ')
    return t('pred.fields.' + b, b) + ' = ' + v
  }
  return t('pred.fields.' + label, label)
}

function CoefList({ rows, color, t }) {
  const max = Math.max(...rows.map(r => Math.abs(r.coef)), 1e-9)
  return rows.map(r => (
    <div className="bar" key={r.label}>
      <span className="lbl" style={{ width: 210, fontSize: 12.5 }}>{fieldLabel(t, r.label)}</span>
      <div className="track"><div className="fill" style={{ width: (100 * Math.abs(r.coef) / max) + '%', background: color }} /></div>
      <span className="val" style={{ width: 130 }}>{r.coef > 0 ? '+' : ''}{r.coef.toFixed(2)} · {t('xai.or')} {r.odds_ratio}</span>
    </div>))
}

export default function Xai() {
  const { t } = useTranslation()
  const [g, setG] = useState(null)
  const [cls, setCls] = useState('High')
  const [err, setErr] = useState(null)
  const [lr, setLr] = useState(null)
  const vm = useViewMode()
  const [full, setFull] = useState(false)
  useEffect(() => {
    get('/api/experiments/baseline/results').then(d => {
      const row = d.results.find(r => r.config === 'A_Risk_PRE-EXEC' && r.model === 'Logistic Regression')
      if (row) setLr(row)
    }).catch(() => {})
    get('/api/explain/global').then(setG).catch(e => setErr(e.message && e.message.includes('explanations') ? t('xai.empty') : e.message)) }, [])
  if (err) return <div className="banner err">{t('common.error')}: {err}</div>
  if (!g) return <p className="muted">{t('common.loading')}</p>
  const rows = g.coefficients_per_class[cls]
  const lim = vm === 'present' && !full ? 5 : 8
  const pos = rows.filter(r => r.coef > 0).slice(0, lim)
  const neg = rows.filter(r => r.coef < 0).slice(-lim).reverse()
  const pmax = Math.max(...g.permutation_importance.map(r => r.f1_drop_mean), 1e-9)
  return (
    <>
      <h2>{t('xai.title')}</h2>
      <PageIntro k="xai" />
      <p className="sub">{t('xai.disclaimer')}</p>
      <div className="card" style={{ marginBottom: 16 }}>
        <h3>🏆 {t('xai.winner')}</h3>
        <div className="mono muted" style={{ fontSize: 13 }} dir="ltr">
          {lr ? `Macro-F1 ${lr.f1_macro_mean.toFixed(3)} ± ${lr.f1_macro_std.toFixed(3)} · AUC ${lr.roc_auc_ovr_macro_mean.toFixed(3)}` : '…'}
          <span dir="auto"> · {t('xai.bestLow')}</span></div>
        {g.fit_scope && <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>{t('xai.fitScope')}: <span className="mono">{g.fit_scope}</span></div>}
      </div>
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 14, flexWrap: 'wrap' }}>
          <span className="muted" style={{ fontSize: 13 }}>{t('xai.classSel')}</span>
          <div className="seg" style={{ maxWidth: 300 }}>
            {['Low', 'Medium', 'High'].map(c => (
              <button key={c} className={cls === c ? 'on' : ''} style={cls === c ? { background: RISK_COLORS[c] } : {}}
                      onClick={() => setCls(c)}>{t('risk.' + c)}</button>))}
          </div>
        </div>
        <div className="grid cols2">
          <div>
            <h3>▲ {t('xai.raise')} «{t('risk.' + cls)}»</h3>
            <CoefList rows={pos} color={RISK_COLORS[cls]} t={t} />
          </div>
          <div>
            <h3>▼ {t('xai.lower')}</h3>
            <CoefList rows={neg} color="var(--ink-2)" t={t} />
          </div>
        </div>
      </div>
      {vm === 'present' && !full && (
        <button className="btn ghost" style={{ marginBottom: 16 }} onClick={() => setFull(true)}>
          {t('hero.details')} ▾</button>)}
      {(vm !== 'present' || full) && (
      <div className="card">
        <h3>{t('xai.perm')}</h3>
        {g.permutation_importance.map(r => (
          <div className="bar" key={r.feature}>
            <span className="lbl" style={{ width: 210, fontSize: 12.5 }}>{fieldLabel(t, r.feature)}</span>
            <div className="track"><div className="fill" style={{ width: (100 * Math.max(r.f1_drop_mean, 0) / pmax) + '%', background: 'var(--accent)' }} /></div>
            <span className="val" style={{ width: 130 }}>{r.f1_drop_mean.toFixed(3)} ± {r.f1_drop_std.toFixed(3)}</span>
          </div>))}
        <p className="muted" style={{ fontSize: 12.5, marginTop: 10 }}>{t('xai.permNote')}</p>
      </div>)}
    </>
  )
}
