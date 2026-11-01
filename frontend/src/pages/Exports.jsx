import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { PageIntro } from '../lib/ui'
import { get, post } from '../lib/api'
export default function Exports() {
  const { t } = useTranslation()
  const [files, setFiles] = useState(null)
  const [busy, setBusy] = useState(false)
  const load = () => get('/api/exports/manifest').then(m => setFiles(m.files)).catch(() => setFiles([]))
  useEffect(() => { load() }, [])
  const gen = async () => { setBusy(true); try { const m = await post('/api/exports/generate'); setFiles(m.files) } finally { setBusy(false) } }
  return (<>
    <h2>{t('exp.title')}</h2>
      <PageIntro k="exports" />
    <p className="sub">{t('exp.note')}</p>
    <button className="btn" onClick={gen} disabled={busy} style={{ marginBottom: 16 }}>
      {busy ? t('common.loading') : t('exp.gen')}</button>
    {files === null ? <p className="muted">{t('common.loading')}</p> :
      files.length === 0 ? <div className="banner err">{t('exp.none')}</div> : (() => {
        const pngs = files.filter(f => f.endsWith('.png'))
        const docs = files.filter(f => !f.endsWith('.png') && !f.endsWith('.svg'))
        return (<>
          <div className="grid cols2">
            {pngs.map(f => (
              <div className="card" key={f}>
                <img src={'/exports/' + f} alt={f}
                  style={{ width: '100%', borderRadius: 8, border: '1px solid var(--line)', background: '#fff' }} />
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 8, alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                  <span className="mono" style={{ fontSize: 12 }}>{f.replace('.png', '')}</span>
                  <span style={{ display: 'flex', gap: 8 }}>
                    <a className="btn ghost" style={{ padding: '5px 12px', fontSize: 12, textDecoration: 'none' }}
                       href={'/exports/' + f} download>PNG</a>
                    <a className="btn ghost" style={{ padding: '5px 12px', fontSize: 12, textDecoration: 'none' }}
                       href={'/exports/' + f.replace('.png', '.svg')} download>SVG</a>
                  </span>
                </div>
              </div>))}
          </div>
          <div className="card" style={{ marginTop: 14 }}>
            <h3>{t('exp.attach')}</h3>
            {docs.map(f => (
              <div key={f} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '8px 2px', borderBottom: '1px solid var(--line)' }}>
                <span className="mono" style={{ fontSize: 12.5 }}>{f}</span>
                <a className="btn ghost" style={{ padding: '4px 12px', fontSize: 12, textDecoration: 'none' }}
                   href={'/exports/' + f} download>⬇ {t('exp.dl')}</a>
              </div>))}
          </div>
        </>)
      })()}
  </>)
}
