import { useSyncExternalStore } from 'react'
let mode = localStorage.getItem('viewMode') || 'present'
const subs = new Set()
export const setViewMode = m => { mode = m; try { localStorage.setItem('viewMode', m) } catch {}; subs.forEach(f => f()) }
export const useViewMode = () => useSyncExternalStore(
  f => { subs.add(f); return () => subs.delete(f) }, () => mode)
