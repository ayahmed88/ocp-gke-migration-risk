import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { PageIntro, useCountUp } from '../lib/ui'
import { useViewMode } from '../lib/viewMode'
import { get } from '../lib/api'

const WRITING = ['front_matter', 'ch1', 'ch2', 'ch3', 'ch4', 'ch5', 'ch6']

function Hero({ p, vm, t }) {
  const n = useCountUp(p.overall_pct, 1700, 0)
  const [w, setW] = useState(0)
  useEffect(() => { const id = setTimeout(() => setW(p.overall_pct), 80); return () => clearTimeout(id) }, [p.overall_pct])
  const doneItems = p.chapters.reduce((a, c) => a + c.done, 0)
  const totalItems = p.chapters.reduce((a, c) => a + c.total, 0)
  const fullGroups = p.chapters.filter(c => c.pct === 100).length
  const liveItems = p.chapters.reduce((a, c) => a + c.items.filter(x => x.auto).length, 0)
  const writing = p.chapters.filter(c => WRITING.includes(c.id))
  const writingDone = writing.length > 0 && writing.every(c => c.pct === 100)
  return (
    <div className="card" style={{ marginBottom: 16, padding: '26px 26px 20px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 26, flexWrap: 'wrap' }}>
        <div style={{ textAlign: 'center' }}>
          <div className="muted" style={{ fontSize: 13 }}>{t('prog.overall')}</div>
          <div className="hero-num" dir="ltr">{n}<span style={{ fontSize: 34 }}>%</span></div>
        </div>
        <div style={{ flex: 1, minWidth: 240 }}>
          <div className="track" style={{ height: 14, background: 'var(--surface-2)', borderRadius: 999, overflow: 'hidden' }}>
            <div style={{ width: w + '%', height: '100%', borderRadius: 999, background: 'var(--accent)',
              transition: 'width 1.4s cubic-bezier(.2,.7,.2,1)' }} />
          </div>
          <div style={{ display: 'flex', gap: 10, marginTop: 12, flexWrap: 'wrap' }}>
            <span className="chip"><b className="mono" dir="ltr">{doneItems}/{totalItems}</b> {t('prog.items')}</span>
            <span className="chip ok"><b className="mono" dir="ltr">{fullGroups}/{p.chapters.length}</b> {t('prog.groups')}</span>
            <span className="chip">⚡ <b className="mono" dir="ltr">{liveItems}</b> {t('prog.live')}</span>
          </div>
        </div>
      </div>
      {writingDone && (
        <p style={{ color: 'var(--risk-medium)', fontWeight: 700, fontSize: 14, margin: '14px 0 2px' }}>
          ✍️ {t('prog.writingDone')}</p>)}
      {vm !== 'present' && (
        <div className="muted" style={{ fontSize: 12, marginTop: 10 }}>
          {t('prog.edit')} <span className="mono" dir="ltr">{p.editable_at}</span> · ⚡ {t('prog.auto')}</div>)}
    </div>)
}

function GroupCard({ ch, i, t }) {
  const pc = useCountUp(ch.pct, 1200, 0, 300 + i * 120)
  const [w, setW] = useState(0)
  useEffect(() => { const id = setTimeout(() => setW(ch.pct), 140 + i * 120); return () => clearTimeout(id) }, [ch.pct, i])
  const complete = ch.pct === 100
  const next = ch.id === 'defense'
  return (
    <div className="card" style={{
      borderColor: complete ? 'color-mix(in srgb, var(--ok) 45%, var(--line))'
        : next ? 'color-mix(in srgb, var(--risk-medium) 55%, var(--line))' : undefined }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <b style={{ fontSize: 13.5, color: next ? 'var(--risk-medium)' : undefined }}>{ch.title}</b>
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span className="mono" dir="ltr" style={{ fontWeight: 700,
            color: complete ? 'var(--ok)' : next ? 'var(--risk-medium)' : 'var(--accent)' }}>{pc}%</span>
          {complete && <span title={t('prog.done')} style={{ width: 22, height: 22, borderRadius: '50%',
            display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontWeight: 800, fontSize: 13,
            background: 'color-mix(in srgb, var(--ok) 16%, transparent)', color: 'var(--ok)' }}>✓</span>}
        </span>
      </div>
      <div className="track" style={{ height: 8, background: 'var(--surface-2)', borderRadius: 999, marginBottom: 10, overflow: 'hidden' }}>
        <div style={{ width: w + '%', height: '100%', borderRadius: 999,
          background: complete ? 'var(--ok)' : next ? 'var(--risk-medium)' : 'var(--accent)',
          transition: 'width 1s cubic-bezier(.2,.7,.2,1)' }} />
      </div>
      {ch.items.map(it => (
        <div key={it.title} style={{ display: 'flex', gap: 8, alignItems: 'baseline', fontSize: 12.5, padding: '3px 0' }}>
          <span style={{ color: it.done ? 'var(--ok)' : 'var(--ink-2)' }}>{it.done ? '✓' : '○'}</span>
          <span className={it.done ? '' : 'muted'}>{it.title}</span>
          {it.auto && <span className="chip" style={{ fontSize: 10, padding: '1px 8px' }}>⚡ {t('prog.auto')}</span>}
        </div>))}
    </div>)
}

export default function Progress() {
  const { t } = useTranslation()
  const vm = useViewMode()
  const [err, setErr] = useState(null)
  const [p, setP] = useState(null)
  useEffect(() => { get('/api/research/progress').then(setP).catch(e => setErr(e.message)) }, [])
  if (err) return <div className="banner err">{t('common.error')}: {err}</div>
  if (!p) return <p className="muted">{t('common.loading')}</p>
  return (<>
    <h2>{t('prog.title')}</h2>
    <PageIntro k="progress" />
    <Hero p={p} vm={vm} t={t} />
    <div className="grid cols2">
      {p.chapters.map((ch, i) => <GroupCard key={ch.id} ch={ch} i={i} t={t} />)}
    </div>
  </>)
}
