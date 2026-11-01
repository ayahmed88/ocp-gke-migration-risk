import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { applyLang } from './i18n'
import Dashboard from './pages/Dashboard'
import Training from './pages/Training'
import Results from './pages/Results'
import Predict from './pages/Predict'
import Xai from './pages/Xai'
import Models from './pages/Models'
import Recommend from './pages/Recommend'
import Progress from './pages/Progress'
import Dictionary from './pages/Dictionary'
import Quality from './pages/Quality'
import Exports from './pages/Exports'
import Vault from './pages/Vault'
import Present from './pages/Present'
import { useViewMode, setViewMode } from './lib/viewMode'
import DocsGuide from './pages/DocsGuide'
import { get } from './lib/api'

const I = {
  gauge: <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 20a8 8 0 1 1 8-8"/><path d="M12 12l4-3"/></svg>,
  flask: <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 3h6M10 3v6l-5.5 9A2 2 0 0 0 6.2 21h11.6a2 2 0 0 0 1.7-3L14 9V3"/></svg>,
  table: <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/></svg>,
  target: <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4.5"/><circle cx="12" cy="12" r="1"/></svg>,
  spark: <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8"/></svg>,
  clip: <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 4V3h6v2H9zM8.5 11l2 2 4-4.5M8.5 17h7"/></svg>,
  screen: <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 21h8M12 16v5"/></svg>,
  life: <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M5.5 5.5l3.7 3.7M18.5 5.5l-3.7 3.7M5.5 18.5l3.7-3.7M18.5 18.5l-3.7-3.7"/></svg>,
  flag: <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 21V4c4-2 8 2 12 0v10c-4 2-8-2-12 0"/></svg>,
  book: <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M4 19a2 2 0 0 1 2-2h14V3H6a2 2 0 0 0-2 2v14zM4 19a2 2 0 0 0 2 2h14"/></svg>,
  shield: <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z"/><path d="M8.5 12l2.5 2.5 4.5-5"/></svg>,
  dl: <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 3v12m0 0l-4-4m4 4l4-4M4 21h16"/></svg>,
  safe: <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M8 4v5M12 14v3M8.5 14h7"/></svg>,
  box: <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 8l-9-5-9 5v8l9 5 9-5V8z"/><path d="M3 8l9 5 9-5M12 13v8"/></svg>,
}

const PAGES = [
  { id: 'dashboard', icon: I.gauge, el: Dashboard },
  { id: 'progress', icon: I.flag, el: Progress },
  { id: 'present', icon: I.screen, el: Present },
  { id: 'training', icon: I.flask, el: Training },
  { id: 'results', icon: I.table, el: Results },
  { id: 'xai', icon: I.spark, el: Xai },
  { id: 'predict', icon: I.target, el: Predict },
  { id: 'recommend', icon: I.clip, el: Recommend },
  { id: 'dictionary', icon: I.book, el: Dictionary },
  { id: 'quality', icon: I.shield, el: Quality },
  { id: 'exports', icon: I.dl, el: Exports },
  { id: 'vault', icon: I.safe, el: Vault },
  { id: 'models', icon: I.box, el: Models },
  { id: 'docsguide', icon: I.life, el: DocsGuide },
]

export default function App() {
  const { t, i18n } = useTranslation()
  const [page, setPage] = useState('dashboard')
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light')
  const [ver, setVer] = useState('')
  const [live, setLive] = useState(false)
  const [seed, setSeed] = useState(42)
  const [hasRun, setHasRun] = useState(true)
  const vm = useViewMode()
  useEffect(() => {
    get('/api/health').then(d => setVer(d.build)).catch(() => {})
    
    const poll = () => get('/api/experiments/baseline/status').then(s2 => { setLive(s2.status === 'running'); if (s2.last_seed != null) setSeed(s2.last_seed); setHasRun(!!s2.last_run_at) }).catch(() => {})
    poll(); const id = setInterval(poll, 6000); return () => clearInterval(id)
  }, [])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('theme', theme)
  }, [theme])

  const toggleLang = () => {
    const next = i18n.language === 'ar' ? 'en' : 'ar'
    i18n.changeLanguage(next); applyLang(next)
  }
  const Page = PAGES.find(p => p.id === page).el

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <h1>{t('app.title')}</h1>
          <p>{t('app.subtitle')}</p>
        </div>
        {PAGES.map(p => (
          <button key={p.id} className={'navbtn' + (page === p.id ? ' active' : '')}
                  onClick={() => setPage(p.id)}>
            {p.icon}{t('nav.' + p.id)}
          </button>
        ))}
      </aside>
      <div className="main">
        <div className="topbar">
          <span className="tag" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span className="chip" style={{ color: live ? 'var(--risk-medium)' : (hasRun ? 'var(--ok)' : 'var(--mut)') }}>
              <span className="dot" />{t('mode.' + (live ? 'live' : (hasRun ? 'demo' : 'reset')))}</span>
            {ver} · seed <b style={{ color: seed !== 42 ? 'var(--warn, #E7B54A)' : 'inherit', fontWeight: seed !== 42 ? 700 : 'inherit' }}>{seed}</b> · 176×27</span>
          <div className="switches">
            <div className="segswitch" style={{ marginInlineEnd: 6 }}>
              <button className={vm === 'present' ? 'on' : ''} onClick={() => setViewMode('present')}>{t('app.modePresent')}</button>
              <button className={vm === 'expert' ? 'on' : ''} onClick={() => setViewMode('expert')}>{t('app.modeExpert')}</button>
            </div>
            <button className="switch" onClick={toggleLang}>
              {i18n.language === 'ar' ? 'English' : 'العربية'}
            </button>
            <button className="switch" onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}>
              {theme === 'light' ? '🌙 ' + t('theme.dark') : '☀️ ' + t('theme.light')}
            </button>
          </div>
        </div>
        <div className="content pagefx" key={page}><Page go={setPage} /></div>
        <footer style={{ textAlign: 'center', padding: '14px 18px', fontSize: 12.5,
                         color: 'var(--ink-2)', borderTop: '1px solid var(--line)' }}>
          {t('app.footer')}
        </footer>
      </div>
    </div>
  )
}
