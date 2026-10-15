import { useEffect, useRef, useState } from 'react'

/** Measures an element's width so SVG units equal CSS pixels (labels stay crisp and sized in px). */
export function useMeasure<T extends HTMLElement>(initial = 340) {
  const ref = useRef<T>(null)
  const [width, setWidth] = useState(initial)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const ro = new ResizeObserver(() => setWidth(Math.max(120, Math.round(el.getBoundingClientRect().width))))
    ro.observe(el)
    setWidth(Math.max(120, Math.round(el.getBoundingClientRect().width)))
    return () => ro.disconnect()
  }, [])
  return [ref, width] as const
}

export const linear = (d0: number, d1: number, r0: number, r1: number) => (v: number) => r0 + ((v - d0) / (d1 - d0 || 1)) * (r1 - r0)
