import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { PageIntro } from '../lib/ui'
import { get } from '../lib/api'

const PRIO_COLOR = { high: 'var(--risk-high)', medium: 'var(--risk-medium)', low: 'var(--ink-2)' }
export const trigText = (tr) => {
  if (tr === 'fallback') return '—'
  if (tr.any) return tr.any.map(trigText).join('  |  ')
  if (tr.all) return tr.all.map(trigText).join('  &  ')
  const v = Array.isArray(tr.value) ? `{${tr.value.join(', ')}}` : tr.value
  return `${tr.field} ${tr.op} ${v}`
}

export default function Recommend() {
  const { t } = useTranslation()
  const [err, setErr] = useState(null)
  const [rules, setRules] = useState(null)
  useEffect(() => { get('/api/recommend/rules').then(d => setRules(d.rules)).catch(e => setErr(e.message)) }, [])
  if (err) return <div className="banner err">{t('common.error')}: {err}</div>
  if (!rules) return <p className="muted">{t('common.loading')}</p>
  return (
    <>
      <h2>{t('rec.title')}</h2>
      <PageIntro k="recommend" />
      <p className="sub">{t('rec.sub')}</p>
      <div className="banner ok" style={{ marginBottom: 16, fontSize: 13 }}>⚖️ {t('rec.gov')}</div>
      <div className="grid cols2">
        {rules.map(r => (
          <div className="card" key={r.id}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <b>{r.id} · {t('rec.actions.' + r.action + '.name')}</b>
              <span className="chip" style={{ color: PRIO_COLOR[r.priority] }}>
                <span className="dot" />{t('rec.prio.' + r.priority)}</span>
            </div>
            <div className="muted" style={{ fontSize: 13, marginBottom: 10 }}>{t('rec.actions.' + r.action + '.desc')}</div>
            <div className="mono" style={{ fontSize: 12, marginBottom: 6 }}>{t('rec.trigger')}: {trigText(r.trigger)}</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <span className="chip">{t('rec.stage.' + r.stage)}</span>
              <span className="chip" title={r.evidence}>📜 {t('rec.evidence')}</span>
            </div>
            <div className="muted" style={{ fontSize: 11.5, marginTop: 8 }}>{r.evidence}</div>
          </div>))}
      </div>
    </>
  )
}
