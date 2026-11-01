import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { PageIntro } from '../lib/ui'
import { get } from '../lib/api'
const COLOR = { PASS: 'var(--ok)', REVIEW: 'var(--risk-medium)', FAIL: 'var(--risk-high)' }
export default function Quality() {
  const { t } = useTranslation()
  const [err, setErr] = useState(null)
  const [q, setQ] = useState(null)
  useEffect(() => { get('/api/dataset/quality').then(setQ).catch(e => setErr(e.message)) }, [])
  if (err) return <div className="banner err">{t('common.error')}: {err}</div>
  if (!q) return <p className="muted">{t('common.loading')}</p>
  return (<>
    <h2>{t('qual.title')}</h2>
      <PageIntro k="quality" />
    {q.checks.map(c => (
      <div className="card" key={c.name} style={{ marginBottom: 10, display: 'flex', gap: 14, alignItems: 'baseline', flexWrap: 'wrap' }}>
        <span className="chip" style={{ color: COLOR[c.status] }}><span className="dot" />{t('qual.status.' + c.status)}</span>
        <div><b style={{ fontSize: 13.5 }}>{c.name}</b>
          <div className="muted mono" style={{ fontSize: 12 }}>{c.detail}</div></div>
      </div>))}
    {q.pending_decisions.length > 0 && (
      <div className="card"><h3>⏸ {t('qual.pending')}</h3>
        {q.pending_decisions.map((l, i) => <div key={i} className="mono muted" style={{ fontSize: 12, margin: '6px 0' }}>{l}</div>)}
      </div>)}
  </>)
}
