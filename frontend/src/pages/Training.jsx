import React, { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { PageIntro } from '../lib/ui'
import { get, post, sse } from '../lib/api'

export default function Training({ go }) {
  const { t } = useTranslation()
  const [status, setStatus] = useState('idle')
  const [cur, setCur] = useState(null)          // {config, model}
  const [folds, setFolds] = useState(0)
  const [doneModels, setDoneModels] = useState([])
  const [err, setErr] = useState(null)
  const [seed, setSeed] = useState('')
  const [secs, setSecs] = useState(0)
  const [done, setDone] = useState(0)
  const [total, setTotal] = useState(null)
  const [lastDur, setLastDur] = useState(null)
  const [lastAt, setLastAt] = useState(null)
  const [lastSeed, setLastSeed] = useState(null)
  const fmtTs = (iso) => iso ? iso.slice(0, 16).replace('T', ' · ') : ''
  const unitRef = React.useRef({ avg: null, marks: [] })
  const fmt = (x) => x >= 60 ? `${Math.floor(x/60)}m ${String(x%60).padStart(2,'0')}s` : `${x}s`
  const esRef = useRef(null)

  const onEvent = (e) => {
    if (e.type === 'experiment_started') { setTotal(e.total_units); setDone(0) }
    if (e.type === 'model_started') { setCur({ config: e.config, model: e.model }); setFolds(0) }
    if (e.type === 'fold_done') {
      setFolds(e.fold); setDone(d => d + 1)
      const u = unitRef.current; u.marks.push(Date.now())
      if (u.marks.length > 9) u.marks.shift()
      if (u.marks.length >= 4) u.avg = (u.marks[u.marks.length - 1] - u.marks[0]) / (u.marks.length - 1) / 1000
    }
    if (e.type === 'model_done') setDoneModels(d => [...d, e])
    if (e.type === 'experiment_finished') {
      setStatus('finished')
      get('/api/experiments/baseline/status')
        .then(st => {
          if (st.duration_s) setSecs(Math.round(st.duration_s))
          if (st.last_run_at) setLastAt(st.last_run_at)
          if (st.last_seed != null) setLastSeed(st.last_seed)
        }).catch(() => {})
    }
    if (e.type === 'error') { setStatus('error'); setErr(e.detail) }
  }
  const attach = () => { esRef.current = sse('/api/experiments/baseline/stream', onEvent) }
  const start = async () => {
    setDoneModels([]); setErr(null); setStatus('running')
    setSecs(0); setDone(0); setTotal(null); setLastDur(null)
    try { await post('/api/experiments/baseline/start', seed !== '' ? { seed: Number(seed) } : {}) } catch (e) {
      if (!String(e.message).includes('already')) { setStatus('error'); setErr(e.message); return }
    }
    attach()
  }
  useEffect(() => {
    get('/api/experiments/baseline/status').then(s => {
      if (s.status === 'running') {
        setStatus('running'); attach()
        setSecs(Math.floor(s.elapsed_s || 0))
        setDone(s.done_units || 0); setTotal(s.total_units)
        setDoneModels(s.completed || [])
        if (s.last_seed != null) setLastSeed(s.last_seed)
        if (s.recent_unit_s) unitRef.current.avg = s.recent_unit_s
        const le = s.last_event
        if (le && le.type === 'fold_done') { setCur({ config: le.config, model: le.model }); setFolds(le.fold) }
      } else if (s.status === 'finished' && s.duration_s) {
        setLastDur(Math.round(s.duration_s))
        setStatus('finished'); setSecs(Math.round(s.duration_s))
        setDoneModels(s.completed || []); setLastAt(s.last_run_at)
        if (s.last_seed != null) setLastSeed(s.last_seed)
      } else if (s.last_run_at) {
        setLastAt(s.last_run_at)
        if (s.last_seed != null) setLastSeed(s.last_seed)
        if (s.last_wall_s) setLastDur(Math.round(s.last_wall_s))
      }
    })
    return () => esRef.current && esRef.current.close()
  }, [])
  useEffect(() => {
    if (status !== 'running') return
    const id = setInterval(() => setSecs(x => x + 1), 1000)
    return () => clearInterval(id)
  }, [status])

  const grouped = {}
  doneModels.forEach(m => { (grouped[m.config] = grouped[m.config] || []).push(m) })

  return (
    <>
      <h2>{t('train.title')}</h2>
      <PageIntro k="training" />
      <p className="sub mono">{t('train.desc')} · {t('train.seedTag')} {lastSeed ?? 42}{(lastSeed ?? 42) !== 42 ? ' ' + t('train.declared') : ''}</p>
      {status === 'idle' && lastAt && (
        <div className="banner ok" style={{ marginBottom: 14, display: 'flex', gap: 14, alignItems: 'center', flexWrap: 'wrap' }}>
          ✅ {t('train.lastAt')}: <b className="mono" style={{ fontSize: 13 }}>{fmtTs(lastAt)}</b>
          {lastSeed != null ? <span>· {t('train.seedTag')} <b className="mono">{lastSeed}</b></span> : null}
          {lastDur ? <span>— {t('train.doneIn')} {fmt(lastDur)}</span> : null}
          <button className="btn ghost" style={{ fontSize: 13 }} onClick={() => go && go('results')}>{t('train.seeResults')}</button>
        </div>)}
      {status === 'running' && <div className="banner ok" style={{ marginBottom: 14 }}>{t('train.resume')}</div>}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 14, alignItems: 'end', flexWrap: 'wrap' }}>
          <button className="btn" onClick={start} disabled={status === 'running'}>
            {status === 'running' ? t('train.running') : t('train.start')}
          </button>
          <div className="field" style={{ width: 230 }}>
            <label>{t('train.seedLabel')}</label>
            <input type="number" value={seed} placeholder={t('train.seedPh')}
                   onChange={e => setSeed(e.target.value)} disabled={status === 'running'} />
          </div>
          {status === 'running' && <span className="chip"><span className="dot" />⏱ {fmt(secs)}{total ? ` · ${done}/${total}` : ''}{total && (unitRef.current.avg || done > 5) ? ` · ${t('train.left')} ≈ ${fmt(Math.max(1, Math.round((unitRef.current.avg || secs / done) * (total - done))))}` : ''}</span>}
          {status === 'finished' && secs > 0 && <span className="chip ok"><span className="dot" />⏱ {t('train.doneIn')} {fmt(secs)}{lastSeed != null ? ` · ${t('train.seedTag')} ${lastSeed}` : ''}{lastAt ? ` · ${fmtTs(lastAt)}` : ''}</span>}
        </div>
        {status === 'running' && cur && (
          <div style={{ marginTop: 16 }}>
            <div className="muted" style={{ marginBottom: 8, fontSize: 13 }}>
              <b>{cur.config}</b> · {cur.model} — {t('train.foldTape')}
            </div>
            <div className="foldtape">
              {Array.from({ length: 25 }, (_, i) => <span key={i} className={i < folds ? 'on' : ''} />)}
            </div>
          </div>
        )}
        {status === 'finished' && (
          <div className="banner ok" style={{ marginTop: 14 }}>
            {t('train.done')} — <button className="btn ghost" onClick={() => go('results')}>{t('train.viewResults')}</button>
          </div>
        )}
        {status === 'error' && <div className="banner err" style={{ marginTop: 14 }}>{t('train.err')}: {err}</div>}
      </div>
      {Object.entries(grouped).map(([cfg, models]) => (
        <div className="card" key={cfg} style={{ marginBottom: 14 }}>
          <h3 style={{ marginBottom: 2 }}>{t(`cfg.${cfg}.name`, cfg)}
            <span className="mono muted" style={{ fontSize: 11, marginInlineStart: 8, fontWeight: 400 }}>{cfg}</span></h3>
          <p className="muted" style={{ fontSize: 12, marginTop: 0 }}>{t(`cfg.${cfg}.sub`, '')}</p>
          <table className="tbl"><thead><tr>
            <th>{t('res.cols.model')}</th><th>Macro-F1</th><th>{t('res.cols.acc')}</th><th>AUC</th><th>{t('res.cols.time')}</th>
          </tr></thead><tbody>
            {models.map(m => (
              <tr key={m.model}>
                <td className="txt">{m.model}</td>
                <td>{m.f1_macro.toFixed(3)} ± {m.f1_macro_std.toFixed(3)}</td>
                <td>{m.accuracy.toFixed(3)}</td><td>{m.auc.toFixed(3)}</td>
                <td>{m.seconds}{t('common.seconds')}</td>
              </tr>))}
          </tbody></table>
        </div>
      ))}
    </>
  )
}
