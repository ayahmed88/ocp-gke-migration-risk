import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { get } from '../lib/api'
import { PageIntro } from '../lib/ui'

export default function Dictionary() {
  const { t } = useTranslation()
  const [err, setErr] = useState(null)
  const [rows, setRows] = useState(null)
  const [q, setQ] = useState('')
  useEffect(() => { get('/api/dataset/dictionary').then(d => setRows(d.dictionary)).catch(e => setErr(e.message)) }, [])
  if (err) return <div className="banner err">{t('common.error')}: {err}</div>
  if (!rows) return <p className="muted">{t('common.loading')}</p>
  const cols = t('dict.cols', { returnObjects: true })
  const keys = ['column','meaning','type','typical','missing','unique','role','pre_exec','leakage','encoding','static_per_service']
  const isOfficial = r => r.role === 'Feature' && r.pre_exec === 'Yes'
  const qq = q.trim().toLowerCase()
  const shown = rows.filter(r => !qq || r.column.toLowerCase().includes(qq) || String(r.meaning).toLowerCase().includes(qq))
  return (<>
    <h2>{t('dict.title')}</h2>
      <PageIntro k="dictionary" />
    <div style={{ display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap', marginBottom: 12 }}>
      <input value={q} onChange={e => setQ(e.target.value)} placeholder={t('dict.search')}
        style={{ width: 300 }} />
      <span className="muted" style={{ fontSize: 12.5 }}>
        <span style={{ display: 'inline-block', width: 12, height: 12, background: 'var(--accent)',
          borderRadius: 3, verticalAlign: 'middle', marginInlineEnd: 6 }} />{t('dict.legend')}</span>
    </div>
    <div className="card" style={{ overflowX: 'auto' }}>
      <table className="tbl"><thead><tr>{cols.map(c => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>{shown.map(r => {
          const off = isOfficial(r)
          return (
          <tr key={r.column} style={off ? { background: 'color-mix(in srgb, var(--accent) 9%, transparent)' } : {}}>
            {keys.map((k, i) => (
              <td key={k} className={k === 'column' ? '' : 'txt'}
                  style={{ fontSize: 12, maxWidth: k === 'meaning' ? 220 : 160,
                           borderInlineStart: off && i === 0 ? '3px solid var(--accent)' : undefined }}>
                {String(r[k])}{off && k === 'column' ? <span className="chip ok" style={{ marginInlineStart: 6, fontSize: 10, padding: '1px 7px' }}>{t('dict.official')}</span> : null}
              </td>))}
          </tr>)})}</tbody></table>
    </div>
  </>)
}
