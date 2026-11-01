import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { PageIntro } from '../lib/ui'
import { get, post } from '../lib/api'

export default function Models() {
  const { t } = useTranslation()
  const [list, setList] = useState(null)
  const [cfg, setCfg] = useState('A_Risk_PRE-EXEC')
  const [busy, setBusy] = useState(false)
  const load = () => get('/api/models').then(d => setList(d.models))
  useEffect(() => { load() }, [])
  const train = async () => { setBusy(true); try { await post('/api/models/train-final', { config: cfg }); await load() } finally { setBusy(false) } }
  return (
    <>
      <h2>{t('models.title')}</h2>
      <PageIntro k="models" />
      <p className="sub">{t('models.note')}</p>
      <div className="card" style={{ marginBottom: 14, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <label className="muted" style={{ fontSize: 13 }}>{t('models.cfg')}</label>
        <select value={cfg} onChange={e => setCfg(e.target.value)} style={{ padding: '9px 11px', borderRadius: 8, border: '1px solid var(--line)', background: 'var(--surface)' }}>
          <option>A_Risk_PRE-EXEC</option><option>B_Risk_FULL</option><option>C_Outcome_PRE-EXEC</option>
        </select>
        <button className="btn" onClick={train} disabled={busy}>{busy ? t('common.loading') : t('models.train')}</button>
        <button className="btn ghost" onClick={load}>{t('common.refresh')}</button>
      </div>
      {!list ? <p className="muted">{t('common.loading')}</p> :
        list.length === 0 ? <div className="banner err">{t('models.empty')}</div> :
        <div className="card" style={{ overflowX: 'auto' }}>
          <table className="tbl"><thead><tr>
            <th>{t('models.cols.algo')}</th><th>{t('models.cols.config')}</th><th>{t('models.cols.target')}</th>
            <th>{t('models.cols.rows')}</th><th>{t('models.cols.at')}</th><th>{t('models.cols.id')}</th>
          </tr></thead><tbody>
            {list.map(m => (
              <tr key={m.model_id}>
                <td className="txt">{m.algorithm}</td><td className="txt" title={m.config} style={{ fontSize: 12 }}>{t(`cfg.${m.config}.name`, m.config)}</td><td>{m.target}</td>
                <td>{m.trained_on_rows}</td><td>{m.trained_at.replace('T', ' ')}</td>
                <td>{m.model_id.slice(-8)}</td>
              </tr>))}
          </tbody></table>
        </div>}
    </>
  )
}
