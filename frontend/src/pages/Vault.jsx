import React, { useEffect, useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { PageIntro } from '../lib/ui'
import { get } from '../lib/api'

const fmtSize = b => b > 1048576 ? (b/1048576).toFixed(1)+' MB' : (b/1024).toFixed(0)+' KB'

export default function Vault() {
  const { t } = useTranslation()
  const [docs, setDocs] = useState(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState(null)
  const [open, setOpen] = useState({})
  const fileRef = useRef(null)
  const load = () => get('/api/vault').then(d => setDocs(d.docs)).catch(() => setDocs([]))
  useEffect(() => { load() }, [])
  const upload = async () => {
    const f = fileRef.current.files[0]
    if (!f) return
    setBusy(true); setMsg(null)
    try {
      const fd = new FormData(); fd.append('file', f); fd.append('note', note)
      const r = await fetch('/api/vault/upload', { method: 'POST', body: fd })
      if (!r.ok) throw new Error((await r.json()).detail || r.status)
      const e = await r.json()
      setMsg(`${t('vault.uploaded')} v${e.n}`); setNote(''); fileRef.current.value = ''; load()
    } catch (e) { setMsg(String(e.message)) } finally { setBusy(false) }
  }
  return (
    <>
      <h2>{t('vault.title')}</h2>
      <PageIntro k="vault" />
      <p className="sub">{t('vault.sub')}</p>
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, alignItems: 'end', flexWrap: 'wrap' }}>
          <div className="field"><label>{t('vault.choose')}</label><input type="file" ref={fileRef} /></div>
          <div className="field" style={{ flex: 1, minWidth: 220 }}>
            <label>{t('vault.note')}</label>
            <input value={note} onChange={e => setNote(e.target.value)} placeholder="…" /></div>
          <button className="btn" onClick={upload} disabled={busy}>
            {busy ? t('vault.uploading') : t('vault.upload')}</button>
        </div>
        {msg && <div className="banner ok" style={{ marginTop: 10, fontSize: 13 }}>{msg}</div>}
      </div>
      {docs === null ? <p className="muted">{t('common.loading')}</p> :
       docs.length === 0 ? <div className="banner err">{t('vault.empty')}</div> :
       docs.map(d => (
        <div className="card" key={d.name} style={{ marginBottom: 12 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 10 }}>
            <div>
              <b style={{ fontSize: 14 }}>{d.name}</b>
              <div className="muted mono" style={{ fontSize: 12 }}>
                {t('vault.latest')}: v{d.latest.n} · {d.latest.ts.replace('T',' ')} · {fmtSize(d.latest.size)}</div>
              {d.latest.note && <div className="muted" style={{ fontSize: 12.5 }}>📝 {d.latest.note}</div>}
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <a className="btn" style={{ textDecoration: 'none', fontSize: 13 }}
                 href={`/api/vault/download?name=${encodeURIComponent(d.name)}`}>⬇ {t('vault.dl')}</a>
              <button className="btn ghost" style={{ fontSize: 13 }}
                onClick={() => setOpen(o => ({ ...o, [d.name]: !o[d.name] }))}>
                {t('vault.history')} ({d.versions.length})</button>
            </div>
          </div>
          {open[d.name] && (
            <table className="tbl" style={{ marginTop: 12 }}>
              <thead><tr><th>{t('vault.ver')}</th><th>{t('vault.at')}</th><th>{t('vault.size')}</th><th className="txt">📝</th><th></th></tr></thead>
              <tbody>{d.versions.map(v => (
                <tr key={v.n}><td>v{v.n}</td><td className="mono" style={{ fontSize: 12 }}>{v.ts.replace('T',' ')}</td>
                  <td>{fmtSize(v.size)}</td><td className="txt" style={{ fontSize: 12.5 }}>{v.note || '—'}</td>
                  <td><a href={`/api/vault/download?name=${encodeURIComponent(d.name)}&version=${v.n}`}>⬇</a></td></tr>))}
              </tbody></table>)}
        </div>))}
    </>
  )
}
