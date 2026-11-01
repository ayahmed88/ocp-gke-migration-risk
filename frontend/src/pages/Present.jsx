import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { PageIntro } from '../lib/ui'
import { useViewMode } from '../lib/viewMode'
import { get, post } from '../lib/api'

const RISK_COLORS = { Low: 'var(--risk-low)', Medium: 'var(--risk-medium)', High: 'var(--risk-high)' }
const PRESET = { Environment: 'QA', Service_Category: 'API', Business_Criticality: 'High',
  Complexity_Level: 4, Has_DB_Dependency: 1, DB_Type: 'PostgreSQL', Has_Network_Change: 1,
  Firewall_Rules_Count: 6, External_Integrations_Count: 3, Route_Ingress_Changed: 1,
  Has_Config_Change: 1, Owner_Availability: 'Delayed', Previous_Issues_Count: 2 }

export default function Present({ go }) {
  const { t } = useTranslation()
  const [i, setI] = useState(0)
  const [mode, setMode] = useState(null)
  const [sum, setSum] = useState(null)
  const [hold, setHold] = useState(null)
  const [pred, setPred] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState(null)
  const [arm, setArm] = useState(false)
  const [ctrl, setCtrl] = useState(null)
  const [rc, setRc] = useState(null)
  const vm = useViewMode()
  const [vr, setVr] = useState(null)
  const [vcId, setVcId] = useState('')
  React.useEffect(() => {
    if (i === 4 && !vr) get('/api/holdout/records').then(setVr).catch(() => {})
  }, [i])
  const [vcase, setVcase] = useState(null)
  const [sOpen, setSOpen] = useState(false)
  const [liveSeed, setLiveSeed] = useState(null)
  const [showVr, setShowVr] = useState(false)
  useEffect(() => {
    get('/api/mode').then(setMode).catch(e => setErr(e.message))
    get('/api/experiments/baseline/status').then(st => { if (st.last_seed != null) setLiveSeed(st.last_seed) }).catch(() => {})
    get('/api/dataset/summary').then(setSum).catch(() => {})
    get('/api/holdout').then(setHold).catch(() => {})
  }, [])
  const runPred = async () => {
    setBusy(true); setErr(null)
    try {
      const ms = (await get('/api/models')).models.filter(m => m.config === 'A_Risk_PRE-EXEC' && m.algorithm === 'Logistic Regression')
      if (!ms.length) throw new Error(t('pred.needModels'))
      setPred(await post('/api/predict', { model_id: ms[ms.length - 1].model_id, features: PRESET }))
    } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  const refreshMeta = () => {
    get('/api/mode').then(setMode).catch(() => {})
    get('/api/experiments/baseline/status').then(st => { if (st.last_seed != null) setLiveSeed(st.last_seed) }).catch(() => {})
    get('/api/holdout').then(setHold).catch(() => {})
  }
  const doReset = async () => {
    setCtrl('reset'); setErr(null)
    try { await post('/api/demo/reset?confirm=true', {}); setPred(null); setRc(null); refreshMeta() }
    catch (e) { setErr(e.message) } finally { setArm(false); setCtrl(null) }
  }
  const doRestore = async () => {
    setCtrl('restore'); setErr(null)
    try {
      await post('/api/demo/restore', {})
      const tick = setInterval(async () => {
        const st = await get('/api/experiments/baseline/status')
        if (st.status === 'finished' || st.status === 'error') {
          clearInterval(tick); setCtrl(null); refreshMeta()
          if (st.status === 'error') setErr(st.error)
        }
      }, 2500)
    } catch (e) { setErr(e.message); setCtrl(null) }
  }
  const drawCase = async () => {
    setBusy(true); setErr(null)
    try { setRc(await get('/api/holdout/random_case')) } catch (e) { setErr(e.message) } finally { setBusy(false) }
  }
  const steps = ['s1','s2','s3','s4','s5','s6']
  const Card = ({ children }) => <div className="card" style={{ minHeight: 260 }}>{children}</div>
  const Info = ({ k, v }) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid var(--line)' }}>
      <span className="muted" style={{ fontSize: 13 }}>{k}</span><span className="mono" style={{ fontSize: 13 }}>{v}</span></div>)

  return (
    <>
      <h2>{t('pres.title')}</h2>
      <PageIntro k="present" />
      <p className="sub">{t('pres.sub')}</p>
      <div style={{ position: 'relative', margin: '6px 0 22px', padding: '0 14px' }}>
        <div style={{ position: 'absolute', insetInlineStart: 54, insetInlineEnd: 54, top: 19,
          height: 4, background: 'var(--line)', borderRadius: 2 }} />
        <div style={{ position: 'absolute', insetInlineStart: 54, top: 19, height: 4,
          width: `calc((100% - 108px) * ${i / (steps.length - 1)})`,
          background: 'var(--accent)', borderRadius: 2, transition: 'width .3s' }} />
        <div style={{ display: 'flex', justifyContent: 'space-between', position: 'relative' }}>
          {steps.map((s, k) => {
            const done = k < i, cur = k === i
            return (
              <button key={s} onClick={() => setI(k)} title={t('pres.' + s)}
                style={{ background: 'none', border: 'none', cursor: 'pointer',
                         display: 'flex', flexDirection: 'column', alignItems: 'center',
                         gap: 6, width: 100, padding: 0, fontFamily: 'inherit' }}>
                <span className={cur ? 'glowteal' : ''} style={{
                  width: cur ? 42 : 34, height: cur ? 42 : 34, borderRadius: '50%',
                  display: 'grid', placeItems: 'center', fontWeight: 800,
                  fontSize: cur ? 17 : 14, transition: 'all .25s',
                  background: done || cur ? 'var(--accent)' : 'var(--surface)',
                  color: done || cur ? 'var(--accent-ink)' : 'var(--ink-2)',
                  border: `3px solid ${done || cur ? 'var(--accent)' : 'var(--line)'}` }}>
                  {done ? '✓' : k + 1}</span>
                <span style={{ fontSize: 11.5, fontWeight: cur ? 800 : 500,
                  color: cur ? 'var(--accent)' : 'var(--ink-2)' }}>{t('pres.short.' + s)}</span>
              </button>)
          })}
        </div>
      </div>
      {err && <div className="banner err" style={{ marginBottom: 12 }}>{err}</div>}
      <div className="card" style={{ marginBottom: 14 }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <b style={{ fontSize: 13.5 }}>{t('pres.panel')}</b>
          {!arm
            ? <button className="btn ghost" style={{ fontSize: 13, color: 'var(--risk-high)' }} disabled={!!ctrl}
                onClick={() => setArm(true)}>{ctrl === 'reset' ? t('pres.resetBusy') : t('pres.reset')}</button>
            : <button className="btn" style={{ fontSize: 13, background: 'var(--risk-high)' }}
                onClick={doReset}>{t('pres.resetArm')}</button>}
          <button className="btn" style={{ fontSize: 13 }} disabled={!!ctrl} onClick={doRestore}>
            {ctrl === 'restore' ? t('pres.restoreBusy') : t('pres.restore')}</button>
        </div>
        <p className="muted" style={{ fontSize: 12, marginTop: 8, marginBottom: 0 }}>{t('pres.resetNote')}</p>
      </div>

      {vm === 'present' && (
        <div style={{ background: 'color-mix(in srgb, var(--accent) 10%, var(--surface))',
          border: '1px solid color-mix(in srgb, var(--accent) 35%, var(--line))',
          borderRadius: 'var(--radius)', padding: '10px 16px', marginBottom: 14,
          fontSize: 13.5, color: 'var(--accent)', fontWeight: 600 }}>
          {t('pres.cueLbl')}: «{t('pres.cue.' + steps[i])}»
        </div>)}
      {i === 0 && <Card><h3>1 · {t('pres.s1')}</h3>
        {!mode ? <p className="muted">{t('common.loading')}</p> : <>
          <Info k={t('pres.sysVer')} v={mode.version} />
          <Info k={t('pres.sysData')} v={`${mode.dataset} · ${mode.records} records`} />
          <Info k={t('pres.sysModel')} v={mode.latest_model ? mode.latest_model.algorithm : '—'} />
          <Info k={t('pres.sysTrained')} v={mode.latest_model ? mode.latest_model.trained_at.replace('T',' ') : '—'} />
          <Info k={t('pres.sysResults')} v={(mode.results_generated_at || '—').replace('T',' ')} />
          <Info k={t('pres.sysSeed')} v={`${liveSeed ?? mode.seed}${(liveSeed ?? mode.seed) !== 42 ? ' ' + t('train.declared') : ''}`} />
          <div style={{ marginTop: 12 }}><span className="chip" style={{ color: mode.state === 'live' ? 'var(--risk-medium)' : mode.state === 'reset' ? 'var(--mut)' : 'var(--ok)' }}><span className="dot" />{t('mode.' + (mode.state || 'demo'))}</span></div>
        </>}</Card>}

      {i === 1 && <Card><h3>2 · {t('pres.s2')}</h3>
        {!sum ? <p className="muted">{t('common.loading')}</p> : <>
          <div style={{ display: 'flex', gap: 26, flexWrap: 'wrap', marginBottom: 14 }}>
            <span className="stat">{sum.rows}<small> {t('common.records')}</small></span>
            <span className="stat">{sum.services}<small> × Dev/QA</small></span>
          </div>
          {['High','Medium','Low'].map(c => (
            <div className="bar" key={c}><span className="lbl">{t('risk.'+c)}</span>
              <div className="track"><div className="fill" style={{ width: (100*sum.risk_distribution[c]/sum.rows)+'%', background: RISK_COLORS[c] }} /></div>
              <span className="val">{sum.risk_distribution[c]}</span></div>))}
        </>}</Card>}

      {i === 2 && <Card><h3>3 · {t('pres.s3')}</h3>
        <p style={{ fontSize: 15, lineHeight: 2 }}>{t('pres.meth')} {t('train.seedTag')} {liveSeed ?? 42}{(liveSeed ?? 42) !== 42 ? ' ' + t('train.declared') : ''}.</p></Card>}

      {i === 3 && <Card><h3>4 · {t('pres.s4')}</h3>
        {!hold ? <p className="muted">{t('common.loading')}</p> : <>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 12 }}>
            <span className="chip">Macro-F1 <b className="mono">{hold.metrics.macro_f1}</b></span>
            <span className="chip">AUC <b className="mono">{hold.metrics.auc_ovr_macro}</b></span>
            <span className="chip">{hold.test_rows} {t('pres.holdRows')}</span>
            <span className="chip">{hold.test_services} {t('pres.holdSvc')}</span>
          </div>
          <h3>{t('pres.cmTitle')}</h3>
          <table className="tbl" style={{ maxWidth: 380 }}><thead><tr><th></th>
            {hold.confusion.labels.map(l => <th key={l}>{t('risk.'+l)}</th>)}</tr></thead><tbody>
            {hold.confusion.matrix.map((row, r) => (
              <tr key={r}><td className="txt" style={{ fontWeight: 600 }}>{t('risk.'+hold.confusion.labels[r])}</td>
                {row.map((v, c2) => <td key={c2} style={r===c2?{background:'color-mix(in srgb, var(--ok) 18%, transparent)',fontWeight:700}:{}}>{v}</td>)}</tr>))}
          </tbody></table>
          <p className="muted" style={{ fontSize: 12.5, marginTop: 12 }}>{t('pres.holdNote')}</p>
          <button className="btn" style={{ marginTop: 6 }} onClick={drawCase} disabled={busy}>
            🎲 {busy ? t('common.loading') : t('pres.randomBtn')}</button>
          <button className="btn ghost" style={{ marginTop: 6, marginInlineStart: 10 }}
            onClick={async () => { if (!vr) { try { setVr(await get('/api/holdout/records')) } catch (e) { setErr(e.message); return } } setShowVr(v => !v) }}>
            🗂 {t('pres.vaultRecs')}</button>
          {showVr && vr && (
            <div style={{ marginTop: 14 }}>
              <p className="muted" style={{ fontSize: 12.5, marginBottom: 8 }}>
                {vr.matches_seal ? '✓ ' : ''}{t('pres.vrSeal')} · {t('pres.vrHits')}: {vr.hits}/{vr.total}</p>
              <div style={{ maxHeight: 320, overflowY: 'auto', border: '1px solid var(--line)', borderRadius: 10 }}>
                <table className="tbl" style={{ margin: 0 }}>
                  <thead><tr><th>{t('pres.vrSvc')}</th><th>{t('pres.vrRec')}</th><th>{t('pres.vrEnv')}</th>
                    <th>{t('pres.rcTrue')}</th><th>{t('pres.rcPred')}</th><th></th></tr></thead>
                  <tbody>{vr.records.map(r => (
                    <tr key={r.migration_id}>
                      <td className="mono" style={{ fontSize: 12 }}>{r.service}</td>
                      <td className="mono" style={{ fontSize: 12 }}>{r.migration_id}</td>
                      <td style={{ fontSize: 12 }}>{r.environment}</td>
                      <td style={{ color: RISK_COLORS[r.true], fontWeight: 600, fontSize: 12.5 }}>{t('risk.' + r.true)}</td>
                      <td style={{ color: RISK_COLORS[r.pred], fontWeight: 600, fontSize: 12.5 }}>{t('risk.' + r.pred)}</td>
                      <td style={{ color: r.match ? 'var(--ok)' : 'var(--risk-high)' }}>{r.match ? '✓' : '✗'}</td>
                    </tr>))}
                  </tbody></table>
              </div>
            </div>)}
          {rc && (
            <div style={{ marginTop: 14, border: '1px solid var(--line)', borderRadius: 10, padding: 14 }}>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 8 }}>
                <b className="mono">{rc.migration_id}</b>
                <span className="chip">{t('pres.rcPred')}: <b style={{ color: RISK_COLORS[rc.predicted] }}>{t('risk.' + rc.predicted)}</b></span>
                <span className="chip">{t('pres.rcTrue')}: <b style={{ color: RISK_COLORS[rc.true] }}>{t('risk.' + rc.true)}</b></span>
                <span className="chip" style={{ color: rc.match ? 'var(--ok)' : 'var(--risk-high)' }}>
                  <span className="dot" />{rc.match ? t('pres.rcMatch') : t('pres.rcMiss')}</span>
              </div>
              {['High','Medium','Low'].map(c => (
                <div className="bar" key={c}><span className="lbl">{t('risk.'+c)}</span>
                  <div className="track"><div className="fill" style={{ width: (100*(rc.probabilities[c]||0))+'%', background: RISK_COLORS[c] }} /></div>
                  <span className="val">{(100*(rc.probabilities[c]||0)).toFixed(1)}%</span></div>))}
              <div className="mono muted" style={{ fontSize: 11.5, marginTop: 8 }}>
                {Object.entries(rc.features).map(([k,v]) => `${k}=${v}`).join(' · ')}</div>
              <p className="muted" style={{ fontSize: 12, marginTop: 6, marginBottom: 0 }}>{t('pres.rcNote')}</p>
            </div>)}
        </>}</Card>}

      {i === 4 && <Card><h3>5 · {t('pres.s5')}</h3>
        <button className="btn" onClick={runPred} disabled={busy}>{busy ? t('common.loading') : t('pres.runPred')}</button>
        <div style={{ marginTop: 14 }}>
          <p className="muted" style={{ fontSize: 13, marginBottom: 8 }}>{t('pres.s5pick')}</p>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'center' }}>
            <div style={{ position: 'relative' }}>
              <style>{`.comboRow:hover{background:var(--bg)}`}</style>
              <input value={vcId} placeholder={t('pres.s5choose')} style={{ width: 260 }}
                onFocus={() => setSOpen(true)}
                onBlur={() => setTimeout(() => setSOpen(false), 150)}
                onChange={e => { setVcId(e.target.value); setSOpen(true) }} />
              {sOpen && (() => {
                const q = vcId.toUpperCase()
                const list = (vr ? vr.records : []).filter(r =>
                  !q || r.migration_id.includes(q) || (r.service || '').toUpperCase().includes(q))
                return list.length ? (
                  <div className="card" style={{ position: 'absolute', top: '106%', insetInlineStart: 0,
                    width: 262, maxHeight: 224, overflowY: 'auto', zIndex: 40, padding: 6, margin: 0 }}>
                    {list.map(r => (
                      <div key={r.migration_id} className="comboRow"
                        onMouseDown={() => { setVcId(r.migration_id); setSOpen(false) }}
                        style={{ padding: '7px 10px', cursor: 'pointer', borderRadius: 8,
                                 display: 'flex', justifyContent: 'space-between', gap: 10 }}>
                        <b className="mono" style={{ fontSize: 13 }}>{r.migration_id}</b>
                        <span className="muted" style={{ fontSize: 11.5 }}>{r.service} · {r.environment}</span>
                      </div>))}
                  </div>) : null
              })()}
            </div>
            <button className="btn" disabled={!vcId || busy}
              onClick={async () => {
                setBusy(true); setErr(null)
                const mid = ((vcId.toUpperCase().match(/MIG-\d+/) || [vcId])[0]).trim()
                try { setVcase(await post('/api/holdout/predict_case', { migration_id: mid })) }
                catch (e) { setErr(e.message && e.message.includes('vault') ? t('pres.s5notVault') : e.message) }
                finally { setBusy(false) } }}>
              {t('pres.s5run')}</button>
            <button onClick={() => go && go('predict')}
              style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0,
                       color: 'var(--accent)', fontSize: 13.5, fontFamily: 'inherit',
                       textDecoration: 'underline', textUnderlineOffset: 4 }}>
              {t('pres.s5free')}</button>
          </div>
          <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>{t('pres.s5sealed')}</p>
          {vcase && <div style={{ marginTop: 12, fontSize: 14 }}>
            <b className="mono">{vcase.migration_id}</b> · {t('pres.rcPred')}: <b style={{ color: RISK_COLORS[vcase.predicted] }}>{t('risk.' + vcase.predicted)}</b>
            {' '}({(100 * vcase.probabilities[vcase.predicted]).toFixed(1)}%) · {t('pres.rcTrue')}: <b style={{ color: RISK_COLORS[vcase.true] }}>{t('risk.' + vcase.true)}</b>
            {' '}<span style={{ color: vcase.match ? 'var(--ok)' : 'var(--risk-high)', fontWeight: 700 }}>{vcase.match ? '✓' : '✗'}</span>
          </div>}
        </div>
        {pred && <div style={{ marginTop: 16 }}>
          <span className="stat" style={{ color: RISK_COLORS[pred.prediction] }}>{t('risk.' + pred.prediction)}</span>
          {['High','Medium','Low'].map(c => (
            <div className="bar" key={c}><span className="lbl">{t('risk.'+c)}</span>
              <div className="track"><div className="fill" style={{ width: (100*pred.probabilities[c])+'%', background: RISK_COLORS[c] }} /></div>
              <span className="val">{(100*pred.probabilities[c]).toFixed(1)}%</span></div>))}
          <p style={{ fontSize: 13, marginTop: 10 }}><b>{t('pres.predWhy')}</b></p>
          {pred.recommendations.recommendations.slice(0,3).map(r => (
            <div key={r.rule_id} style={{ fontSize: 13, padding: '4px 0' }}>
              <span className="chip" style={{ marginInlineEnd: 8 }}>{r.rule_id}</span>
              {t('rec.actions.'+r.action+'.name')} <span className="mono muted" style={{ fontSize: 11 }}>({r.triggered_by})</span></div>))}
        </div>}</Card>}

      {i === 5 && <Card><h3>6 · {t('pres.s6')}</h3>
        <p style={{ fontSize: 16, lineHeight: 2.1 }}>{t('pres.closing')}</p>
        <div className="banner ok" style={{ fontSize: 13 }}>⚖️ {t('rec.gov')}</div></Card>}

      <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 16 }}>
        <button className="btn ghost" disabled={i===0} onClick={() => setI(i-1)}>{t('pres.prev')}</button>
        <span className="mono muted">{t('pres.step')} {i+1} / 6</span>
        <button className="btn" disabled={i===5} onClick={() => setI(i+1)}>{t('pres.next')}</button>
      </div>
    </>
  )
}
