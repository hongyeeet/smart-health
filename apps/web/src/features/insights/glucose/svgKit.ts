/** Small helpers for the Glucose page charts: round scales, gap-aware paths, which days get an axis label, and clock labels. */

export type Series = (number | null)[]

export const nums = (xs: Series) => xs.filter((v): v is number => v != null)

/** Grid lines on round numbers: `parts` equal steps up from `lo`. The top is moved up to the last step. */
export function ticks(lo: number, hi: number, parts: number) {
  const step = Math.max(1, Math.ceil((hi - lo) / parts))
  return { lo, hi: lo + step * parts, values: Array.from({ length: parts + 1 }, (_, k) => lo + step * k) }
}

/** Widens [lo, hi] so that every value fits. */
export function fit(vals: number[], lo: number, hi: number): [number, number] {
  let a = lo
  let b = hi
  for (const v of vals) {
    a = Math.min(a, Math.floor(v))
    b = Math.max(b, Math.ceil(v))
  }
  return [a, b]
}

/** A line through the values. A missing reading (null) lifts the pen, so the line does not join across the gap. */
export function linePath(vals: Series, x: (i: number) => number, y: (v: number) => number): string {
  let d = ''
  let open = false
  vals.forEach((v, i) => {
    if (v == null) {
      open = false
      return
    }
    d += `${open ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`
    open = true
  })
  return d
}

/** A filled band between a top and a bottom series, drawn as one shape for each run of days that have both. */
export function bandPath(top: Series, bottom: Series, x: (i: number) => number, y: (v: number) => number): string {
  let d = ''
  let run: number[] = []
  const close = () => {
    if (run.length > 1) {
      const up = run.map((i) => `${x(i).toFixed(1)},${y(top[i] as number).toFixed(1)}`)
      const down = [...run].reverse().map((i) => `${x(i).toFixed(1)},${y(bottom[i] as number).toFixed(1)}`)
      d += `M${up.join('L')}L${down.join('L')}Z`
    }
    run = []
  }
  top.forEach((v, i) => {
    if (v != null && bottom[i] != null) run.push(i)
    else close()
  })
  close()
  return d
}

/** Which day indexes get an axis label: every 7 days (every 30 on a long period), always the first and the last day. */
export function labelDays(n: number): number[] {
  if (n <= 1) return [0]
  const step = n > 31 ? 30 : 7
  const idx: number[] = []
  for (let i = 0; i < n; i += step) idx.push(i)
  const last = idx[idx.length - 1] ?? 0
  if (n - 1 - last >= 4) idx.push(n - 1)
  else idx[idx.length - 1] = n - 1
  return idx
}

export const isWeekend = (iso: string) => {
  const day = new Date(`${iso}T12:00:00`).getDay()
  return day === 0 || day === 6
}

/** A clock hour as a short English label, for example "1 pm" or "12 am". */
export const hourLabel = (h: number) =>
  new Date(2000, 0, 1, h).toLocaleTimeString('en-US', { hour: 'numeric', hour12: true }).replace(/\s+/g, ' ').toLowerCase()
