import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { PageIntro } from '../lib/ui'
import { get } from '../lib/api'
const Cmd = ({ c }) => <div className="mono" style={{ background: 'var(--surface-2)', borderRadius: 8, padding: '8px 12px', fontSize: 12.5, margin: '6px 0', direction: 'ltr', textAlign: 'left' }}>{c}</div>
export default function DocsGuide({ go }) {
  const { t } = useTranslation()
  const [v, setV] = useState('')
  useEffect(() => { get('/api/health').then(d => setV(d.build)).catch(() => {}) }, [])
  return (<>
    <h2>{t('docsg.title')} <span className="mono muted" style={{ fontSize: 14 }}>{v}</span></h2>
    <PageIntro k="docsguide" />
    <div className="grid cols2">
      <div className="card"><h3>🚀 {t('docsg.run')}</h3>
        <Cmd c="docker compose up --build" /><Cmd c="http://localhost:8000" />
        <p className="muted" style={{ fontSize: 12.5 }}>Python fallback:</p>
        <Cmd c=".\.venv\Scripts\Activate.ps1" /><Cmd c="uvicorn backend.api.main:app --port 8000" />
      </div>
      <div className="card"><h3>🎛 {t('docsg.modeT')}</h3><p style={{ fontSize: 13.5 }}>{t('docsg.modeTxt')}</p></div>
      <div className="card"><h3>🛟 {t('docsg.fb')}</h3><p style={{ fontSize: 13.5 }}>{t('docsg.fbTxt')}</p>
        <Cmd c="python -m backend.experiments.algorithm_walkthrough" /></div>
      <div className="card"><h3>🔗 {t('docsg.links')}</h3>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <a className="btn" style={{ fontSize: 13, textDecoration: 'none' }} href="/api/docs/manual">📘 {t('docsg.manualBtn')}</a>
          <a className="btn ghost" style={{ fontSize: 13, textDecoration: 'none' }} href="/docs" target="_blank">{t('docsg.api')}</a>
          <a className="btn ghost" style={{ fontSize: 13, textDecoration: 'none' }} href="/api/dataset/download">⬇ {t('docsg.dataBtn')}</a>
          <button className="btn ghost" style={{ fontSize: 13 }} onClick={() => go && go('exports')}>{t('docsg.exports')}</button>
        </div></div>
    </div>
  </>)
}
