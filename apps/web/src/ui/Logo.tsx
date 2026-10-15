/** The Equinox mark (watch face with a pulse line). Two files, one per theme; the page theme decides which one shows. */
export function Logo({ size = 28, className = '' }: { size?: number; className?: string }) {
  const h = Math.round((size * 600) / 520)
  return (
    <span className={`inline-flex shrink-0 ${className}`} aria-hidden>
      <img src="/equinox-mark.svg" alt="" width={size} height={h} className="[[data-theme=dark]_&]:hidden" />
      <img src="/equinox-mark-dark.svg" alt="" width={size} height={h} className="hidden [[data-theme=dark]_&]:block" />
    </span>
  )
}
