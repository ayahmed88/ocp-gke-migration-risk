export async function get(url) {
  const r = await fetch(url)
  if (!r.ok) throw new Error((await r.json()).detail || r.statusText)
  return r.json()
}
export async function post(url, body) {
  const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined })
  if (!r.ok) throw new Error((await r.json()).detail || r.statusText)
  return r.json()
}
export function sse(url, onEvent, onEnd) {
  const es = new EventSource(url)
  es.onmessage = (m) => {
    const e = JSON.parse(m.data)
    onEvent(e)
    if (e.type === 'experiment_finished' || e.type === 'error') { es.close(); onEnd && onEnd(e) }
  }
  es.onerror = () => { es.close(); onEnd && onEnd({ type: 'disconnected' }) }
  return es
}
