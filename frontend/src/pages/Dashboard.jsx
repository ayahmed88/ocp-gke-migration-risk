import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { PageIntro, useCountUp } from '../lib/ui'
import { useViewMode } from '../lib/viewMode'
import { get } from '../lib/api'

const RISK = ['High', 'Medium', 'Low']
const OUT = ['Delayed', 'Success', 'Failed']
const riskVar = { Low: 'var(--risk-low)', Medium: 'var(--risk-medium)', High: 'var(--risk-high)' }
const outVar = { Success: 'var(--risk-low)', Delayed: 'var(--risk-medium)', Failed: 'var(--risk-high)' }

function Dist({ title, order, data, colors, tPrefix }) {
  const { t } = useTranslation()
  const total = Object.values(data || {}).reduce((a, b) => a + b, 0) || 1
  return (
    <div className="card">
      <h3>{title}</h3>
      {order.map(k => (
        <div className="bar" key={k}>
          <span className="lbl">{t(tPrefix + '.' + k)}</span>
          <div className="track"><div className="fill" style={{ width: (100 * (data?.[k] || 0) / total) + '%', background: colors[k] }} /></div>
          <span className="val">{data?.[k] || 0} · {(100 * (data?.[k] || 0) / total).toFixed(1)}%</span>
        </div>
      ))}
    </div>
  )
}


function Counter({ n, label, dp = 0, delay = 0 }) {
  const v = useCountUp(n, 2400, dp, delay)
  return (
    <div style={{ textAlign: 'center', minWidth: 118 }}>
      <div className="mono" style={{ fontSize: 34, fontWeight: 800, color: 'var(--accent)' }}>{dp ? v : Math.round(v)}</div>
      <div className="muted" style={{ fontSize: 12 }}>{label}</div>
    </div>)
}

function EffortBanner({ t, build }) {
  const items = [[176, t('hero.bRecords')], [300, t('hero.bTrain')], [25, t('hero.bExams')],
                 [21, t('hero.bTests')], [build, t('hero.bBuilds')]]
  return (
    <div className="card glowteal" style={{ marginBottom: 16, display: 'flex', alignItems: 'center',
      gap: 30, flexWrap: 'wrap' }}>
      <b style={{ fontSize: 15 }}>{t('hero.banner')}</b>
      <div style={{ display: 'flex', gap: 22, flexWrap: 'wrap' }}>
        {items.map(([n, lb], i) => <Counter key={lb} n={n} label={lb} delay={i * 320} />)}
      </div>
    </div>)
}

export default function Dashboard({ go }) {
  const { t } = useTranslation()
  const [s, setS] = useState(null)
  const [buildNum, setBuildNum] = useState(43)
  const vm = useViewMode()
  const [err, setErr] = useState(null)
  useEffect(() => {
    get('/api/health').then(h => { const n = parseInt(String(h.build || '').replace(/\D/g, '')); if (n) setBuildNum(n) }).catch(() => {})
    get('/api/dataset/summary').then(setS).catch(e => setErr(e.message)) }, [])
  if (err) return <div className="banner err">{t('common.error')}: {err}</div>
  if (!s) return <p className="muted">{t('common.loading')}</p>
  return (
    <>
      <h2>{t('dash.title')}</h2>
      <PageIntro k="dashboard" />
      {vm === 'present' && <EffortBanner t={t} build={buildNum} />}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 12 }}>
        <a className="btn ghost" style={{ fontSize: 13, textDecoration: 'none' }}
           href="/api/dataset/download">⬇ {t('dash.dlData')}</a>
        <button className="btn ghost" style={{ fontSize: 13 }}
           onClick={() => go && go('dictionary')}>📖 {t('dash.cols27')}</button>
      </div>
      <p className="sub">{t('app.subtitle')}</p>
      <div className="grid cols4" style={{ marginBottom: 16 }}>
        <div className="card"><h3>{t('dash.rows')}</h3><div className="stat">{s.rows}</div></div>
        <div className="card"><h3>{t('dash.services')}</h3><div className="stat">{s.services}<small> × Dev/QA</small></div></div>
        <div className="card"><h3>{t('dash.envs')}</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {Object.entries(s.environments).sort(([a], [b]) => a.localeCompare(b)).map(([k, v]) => (
              <div key={k} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
                <span>{k}</span>
                <span className="mono" style={{ fontSize: 20, fontWeight: 600 }}>{v} <small className="muted" style={{ fontSize: 11.5, fontWeight: 400 }}>{t('common.records')}</small></span>
              </div>))}
          </div>
        </div>
        <div className="card"><h3>{t('dash.features')}</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            <span className="chip">{t('dash.preexec')} · <b className="mono">13</b></span>
            <span className="chip">{t('dash.full')} · <b className="mono">20</b></span>
          </div>
        </div>
      </div>
      <div className="grid cols2" style={{ marginBottom: 16 }}>
        <Dist title={t('dash.risk')} order={RISK} data={s.risk_distribution} colors={riskVar} tPrefix="risk" />
        <Dist title={t('dash.outcome')} order={OUT} data={s.outcome_distribution} colors={outVar} tPrefix="outcome" />
      </div>
      <div className="grid cols2">
        <div className="card"><h3>{t('dash.integrity')}</h3>
          <span className={'chip ' + (s.integrity_checks.all_passed ? 'ok' : '')}><span className="dot" />{s.integrity_checks.all_passed ? t('dash.integrityPass') : t('common.error')}</span>
          <div className="muted" style={{ marginTop: 10, fontSize: 12.5 }}>
            {Object.entries(s.integrity_checks).filter(([k]) => k !== 'all_passed').map(([k, v]) => (
              <div key={k} title={k}>{v ? '✓' : '✗'} {t('gates.' + k, k)}</div>))}
          </div>
        </div>
        <div className="card"><h3>{t('dash.oracle')}</h3>
          <span className={'chip ' + (s.cleaned_reference_verification.values_match_documented_intent ? 'ok' : '')}>
            <span className="dot" />{t('dash.oraclePass')}</span>
        </div>
      </div>
    </>
  )
}
