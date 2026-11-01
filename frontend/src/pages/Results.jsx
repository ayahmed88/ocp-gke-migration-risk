import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { get } from '../lib/api'
import { useViewMode } from '../lib/viewMode'
import { PageIntro, Hint, useCountUp } from '../lib/ui'

const CFGS = ['A_Risk_PRE-EXEC', 'B_Risk_FULL', 'C_Outcome_PRE-EXEC']

function CfgHeader({ cfg, t }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <h3 style={{ margin: 0, fontSize: 16, color: 'var(--ink)' }}>{t(`cfg.${cfg}.name`, cfg)}</h3>
      <div className="muted" style={{ fontSize: 12.5 }}>{t(`cfg.${cfg}.sub`, '')}{' '}
        <span className="mono" style={{ fontSize: 11, opacity: .7 }}>{cfg}</span></div>
    </div>)
}

function ExpertTable({ cfg, rows, t }) {
  const classes = cfg.includes('Outcome') ? ['Success', 'Delayed', 'Failed'] : ['High', 'Medium', 'Low']
  const bestF1 = Math.max(...rows.filter(r => !r.model.includes('Dummy')).map(r => r.f1_macro_mean))
  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <CfgHeader cfg={cfg} t={t} />
      <div style={{ overflowX: 'auto' }}>
        <table className="tbl"><thead><tr>
          <th>{t('res.cols.model')}</th><th><Hint g="macroF1">Macro-F1</Hint></th><th>{t('res.cols.acc')}</th>
          <th>{t('res.cols.bacc')}</th><th><Hint g="auc">AUC</Hint></th>
          <th>{t('res.recall')} ({classes.join(' / ')})</th><th>{t('res.cols.time')}</th>
        </tr></thead><tbody>
          {rows.map(r => (
            <tr key={r.model} className={r.f1_macro_mean === bestF1 ? 'best' : ''}>
              <td className="txt">{t('mdl.' + r.model, r.model)}{r.f1_macro_mean === bestF1 ? ' ★' : ''}</td>
              <td>{r.f1_macro_mean.toFixed(3)} ± {r.f1_macro_std.toFixed(3)}</td>
              <td>{r.accuracy_mean.toFixed(3)}</td>
              <td>{r.balanced_accuracy_mean.toFixed(3)}</td>
              <td>{r.roc_auc_ovr_macro_mean.toFixed(3)}</td>
              <td>{classes.map(c => (r['recall_' + c + '_mean'] ?? 0).toFixed(2)).join(' / ')}</td>
              <td>{r.fit_time_mean_s.toFixed(2)}{t('common.seconds')}</td>
            </tr>))}
        </tbody></table>
      </div>
    </div>)
}

function Bar({ name, v, max, lead, t, delay }) {
  const [w, setW] = useState(0)
  useEffect(() => { const id = setTimeout(() => setW(100 * v / max), 60 + delay); return () => clearTimeout(id) }, [v, max, delay])
  return (
    <div className="bar" style={{ margin: '12px 0' }}>
      <span className="lbl" style={{ width: 170, fontSize: 14, fontWeight: lead ? 800 : 500,
        color: lead ? 'var(--accent)' : 'var(--ink)' }}>{t('mdl.' + name, name)}</span>
      <div className="track" style={{ height: lead ? 20 : 13 }}>
        <div className={'fill' + (lead ? ' glowteal' : '')}
          style={{ width: w + '%', background: lead ? 'var(--accent)' : 'var(--ink-2)', transition: 'width .9s cubic-bezier(.2,.7,.2,1)' }} />
      </div>
      <span className="val" style={{ fontWeight: lead ? 800 : 400 }}>{v.toFixed(3)}</span>
    </div>)
}

function Hero({ rows, m, t }) {
  const lr = rows.find(r => r.model === 'Logistic Regression')
  const dummy = rows.find(r => r.model.includes('Dummy'))
  const anim = useCountUp(lr.f1_macro_mean, 1700)
  const [vault, setVault] = useState(null)
  const [hits, setHits] = useState(null)
  const [open, setOpen] = useState(false)
  useEffect(() => {
    get('/api/holdout').then(h => setVault(h.metrics)).catch(() => {})
    get('/api/holdout/records').then(r => setHits(r.hits)).catch(() => {})
  }, [])
  const ratio = (lr.f1_macro_mean / dummy.f1_macro_mean).toFixed(1)
  const sorted = [...rows].sort((a, b) => b.f1_macro_mean - a.f1_macro_mean)
  return (
    <>
      <div className="card" style={{ marginBottom: 14, padding: '26px 26px 20px' }}>
        <CfgHeader cfg="A_Risk_PRE-EXEC" t={t} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 26, flexWrap: 'wrap', margin: '14px 0 6px' }}>
          <div style={{ textAlign: 'center' }}>
            <div className="muted" style={{ fontSize: 13 }}><Hint g="macroF1">Macro-F1</Hint> — {t('hero.lead')}</div>
            <div className="hero-num">{anim}</div>
            <div className="muted mono" style={{ fontSize: 13 }}><span dir="ltr">± {lr.f1_macro_std.toFixed(3)}</span></div>
          </div>
          <div style={{ display: 'flex', gap: 12 }}>
            {[['AUC', lr.roc_auc_ovr_macro_mean], [t('hero.acc'), lr.accuracy_mean]].map(([lb, vv]) => (
              <div key={lb} className="card" style={{ margin: 0, padding: '12px 18px', textAlign: 'center' }}>
                <div className="muted" style={{ fontSize: 12 }}>{lb}</div>
                <div className="mono" style={{ fontSize: 20, fontWeight: 700 }}>{vv.toFixed(3)}</div>
              </div>))}
          </div>
        </div>
        <p style={{ color: 'var(--risk-medium)', fontWeight: 700, fontSize: 14, margin: '6px 0 14px' }}>
          {t('hero.over', { x: ratio })}</p>
        {sorted.map((r, i) => (
          <Bar key={r.model} name={r.model} v={r.f1_macro_mean} max={0.72}
            lead={r.model === 'Logistic Regression'} t={t} delay={i * 130} />))}
        {vault && (
          <div className="heroVault" style={{ marginTop: 16 }}>
            {t('hero.vault', { f: vault.macro_f1.toFixed(3), h: hits ?? '…' })}
          </div>)}
        <p className="muted" style={{ fontSize: 12.5, margin: '10px 0 14px' }}>⚠️ {t('res.lowNote')}</p>
        <button className="btn ghost" onClick={() => setOpen(o => !o)}>
          {open ? t('hero.hide') : t('hero.details')} {open ? '▴' : '▾'}</button>
      </div>
      {open && CFGS.filter(c => c in groupedRef.current).map(c => (
        <ExpertTable key={c} cfg={c} rows={groupedRef.current[c]} t={t} />))}
    </>)
}

const groupedRef = { current: {} }

export default function Results({ go }) {
  const { t } = useTranslation()
  const vm = useViewMode()
  const [data, setData] = useState(null)
  const [missing, setMissing] = useState(false)
  useEffect(() => {
    get('/api/experiments/baseline/results').then(setData).catch(() => setMissing(true))
  }, [])
  if (missing) return (<><h2>{t('res.title')}</h2>
      <PageIntro k="results" />
    <div className="banner err">{t('res.empty')}</div></>)
  if (!data) return <p className="muted">{t('common.loading')}</p>

  const byCfg = {}
  data.results.forEach(r => { (byCfg[r.config] = byCfg[r.config] || []).push(r) })
  groupedRef.current = byCfg
  const m = data.manifest

  return (
    <>
      <h2>{t('res.title')}</h2>
      <PageIntro k="results" />
      {m && m.split_seed_base != null && (
        <p className="muted" style={{ marginTop: -4, marginBottom: 10, fontSize: 13.5 }}>
          🎲 <Hint g="seed">{t('res.seedLine')}</Hint>: <b className="mono">{m.split_seed_base}</b>
          {m.split_seed_base !== m.seed ? ' ' + t('res.declared') : ''}</p>)}
      {vm === 'present' && byCfg['A_Risk_PRE-EXEC']
        ? <Hero rows={byCfg['A_Risk_PRE-EXEC']} m={m} t={t} />
        : (<>
            <p className="muted" style={{ fontSize: 12.5, marginBottom: 10 }}>⚠️ {t('res.lowNote')}</p>
            <p className="sub mono">{m.dataset} · {m.rows} rows / {m.groups} groups</p>
            {CFGS.filter(c => c in byCfg).map(cfg => (
              <ExpertTable key={cfg} cfg={cfg} rows={byCfg[cfg]} t={t} />))}
          </>)}
      <div className="card">
        <h3><Hint g="manifest">{t('res.manifest')}</Hint></h3>
        <div className="mono" dir="ltr" style={{ fontSize: 12.5, lineHeight: 2, textAlign: "left" }}>
          <div><Hint g="protocol">{t('res.validation')}</Hint>: {m.validation}</div>
          <div>{t('res.seed')}: {m.split_seed_base}{m.split_seed_base !== m.seed ? ' ' + t('res.declared') : ''} · {t('res.tuning')}: {t('res.tuningNone')} · {t('res.primary')}: {m.primary_metric}</div>
          <div>{Object.entries(m.versions).map(([k, v]) => `${k} ${v}`).join(' · ')}</div>
        </div>
      </div>
    </>
  )
}
