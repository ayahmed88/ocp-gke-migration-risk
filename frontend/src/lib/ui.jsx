import React, { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useViewMode } from './viewMode'

export function PageIntro({ k }) {
  const { t } = useTranslation()
  const vm = useViewMode()
  return (
    <details className="pageintro" open={vm === 'present'} key={vm + k}>
      <summary>{t('intro.label')}</summary>
      <p className="muted">{t('intro.' + k)}</p>
    </details>)
}

export function Hint({ g, children }) {
  const { t } = useTranslation()
  return <span className="hint" title={t('gloss.' + g)}>{children}</span>
}

export function useCountUp(target, dur = 900, dp = 3, delay = 0) {
  const [v, setV] = useState(0)
  const ref = useRef()
  useEffect(() => {
    const t0 = performance.now() + delay
    const tick = now => {
      const p = Math.max(0, Math.min(1, (now - t0) / dur))
      setV(target * (1 - Math.pow(1 - p, 3)))
      if (p < 1) ref.current = requestAnimationFrame(tick)
    }
    ref.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(ref.current)
  }, [target])
  return v.toFixed(dp)
}
