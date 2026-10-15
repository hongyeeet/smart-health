import type { Trend } from '@/data/types'
import { TrendChart } from './TrendChart'

/**
 * Fasting glucose, resting heart rate and blood oxygen on the same dates, one above the other, so a
 * clinician can see whether they move together. Each keeps its own scale and its own baseline band.
 */
export function WearableTrends({ fasting, restingHr, spo2, compact = false, keyPrefix }: { fasting: Trend; restingHr: Trend; spo2: Trend; compact?: boolean; keyPrefix: string }) {
  const h = compact ? 96 : 120
  return (
    <div className="flex flex-col gap-3">
      <div>
        <p className="text-sub font-bold text-ink2">Fasting glucose (mmol/L)</p>
        <TrendChart points={fasting.points} baseline={fasting.baseline} label="Fasting glucose" height={h} format={(v) => v.toFixed(1)} drawKey={`${keyPrefix}-g`} />
      </div>
      <div>
        <p className="text-sub font-bold text-ink2">Resting heart rate (beats a minute)</p>
        <TrendChart points={restingHr.points} baseline={restingHr.baseline} label="Resting heart rate" height={h} format={(v) => String(Math.round(v))} drawKey={`${keyPrefix}-h`} color="var(--c-s3)" />
      </div>
      <div>
        <p className="text-sub font-bold text-ink2">Blood oxygen, SpO2 (%)</p>
        <TrendChart points={spo2.points} baseline={spo2.baseline} label="Blood oxygen" height={h} format={(v) => v.toFixed(1)} drawKey={`${keyPrefix}-o`} color="var(--c-s2)" yMin={93} yMax={99} />
      </div>
    </div>
  )
}
