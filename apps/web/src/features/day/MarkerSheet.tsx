import { Sheet } from '@/ui/Sheet'
import { Button, Card, StatusPill, type Tone as PillTone } from '@/ui/primitives'
import { Check, Clock, Question, Warning, X, type IconType } from '@/ui/icons'
import type { DayMarker, DoseState } from './api'
import { doseWords } from './dayMath'

const STATE: Record<DoseState, { tone: PillTone; icon: IconType }> = {
  taken: { tone: 'ok', icon: Check },
  late: { tone: 'warn', icon: Clock },
  not_confirmed: { tone: 'neutral', icon: Question },
  missed: { tone: 'danger', icon: X },
}

const FLAG_WORDS = { salt: 'High salt for one meal', sugar: 'High sugar for one meal' } as const

/**
 * D2, "Marker detail": opened from a marker on the Day view with `go('D2', { sheet: { marker } })`.
 * The outcome sentence is worded from the numbers shown here. It describes what happened together, never a cause.
 */
export function MarkerSheet({ onClose, marker }: { onClose: () => void; marker?: DayMarker } & Record<string, unknown>) {
  if (!marker) {
    return (
      <Sheet title="Details" onClose={onClose}>
        <div className="flex flex-col gap-4">
          <p className="text-body text-ink2">These details are no longer here. Go back to the day and tap the marker again.</p>
          <Button onClick={onClose}>Close</Button>
        </div>
      </Sheet>
    )
  }
  const state = marker.kind === 'dose' && marker.status ? STATE[marker.status] : null
  return (
    <Sheet title={marker.title} label={`${marker.title} at ${marker.clock}`} onClose={onClose}>
      <div className="flex flex-col gap-4">
        <p className="text-body text-ink2">
          {marker.clock}
          {marker.subtitle ? `, ${marker.subtitle}` : ''}
        </p>

        {(state || marker.flags.length > 0) && (
          <div className="flex flex-wrap gap-2">
            {state && marker.status && (
              <StatusPill tone={state.tone} icon={state.icon}>
                {doseWords(marker.status)}
              </StatusPill>
            )}
            {marker.flags.map((f) => (
              <StatusPill key={f} tone="warn" icon={Warning}>
                {FLAG_WORDS[f]}
              </StatusPill>
            ))}
          </div>
        )}

        <Card tone="soft" as="section">
          <h3 className="text-sub font-bold text-ink2">What the data shows</h3>
          <p className="mt-1 text-body text-ink">{marker.outcome}</p>
        </Card>

        {marker.rows.length > 0 && (
          <dl className="flex flex-col divide-y divide-line/70 rounded-card border border-line bg-card">
            {marker.rows.map((r) => (
              <div key={r.label} className="flex items-baseline justify-between gap-4 px-4 py-3">
                <dt className="text-sub text-ink2">{r.label}</dt>
                <dd className="num text-right text-body font-bold text-ink">{r.value}</dd>
              </div>
            ))}
          </dl>
        )}

        <p className="text-sub text-ink3">Things that happen close together are not proof that one caused the other.</p>
        <Button variant="secondary" onClick={onClose}>
          Close
        </Button>
      </div>
    </Sheet>
  )
}
