import { useTranslation } from 'react-i18next'
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

/**
 * D2, "Marker detail": opened from a marker on the Day view with `go('D2', { sheet: { marker } })`.
 * The outcome sentence is worded from the numbers shown here. It describes what happened together, never a cause.
 */
export function MarkerSheet({ onClose, marker }: { onClose: () => void; marker?: DayMarker } & Record<string, unknown>) {
  const { t } = useTranslation()
  const FLAG_WORDS = {
    salt: t('day.flag.salt', 'High salt for one meal'),
    sugar: t('day.flag.sugar', 'High sugar for one meal'),
  } as const
  if (!marker) {
    return (
      <Sheet title={t('day.sheet.details', 'Details')} onClose={onClose}>
        <div className="flex flex-col gap-4">
          <p className="text-body text-ink2">{t('day.sheet.gone', 'These details are no longer here. Go back to the day and tap the marker again.')}</p>
          <Button onClick={onClose}>{t('day.sheet.close', 'Close')}</Button>
        </div>
      </Sheet>
    )
  }
  const state = marker.kind === 'dose' && marker.status ? STATE[marker.status] : null
  return (
    <Sheet title={marker.title} label={t('day.sheet.markerAt', '{{title}} at {{clock}}', { title: marker.title, clock: marker.clock })} onClose={onClose}>
      <div className="flex flex-col gap-4">
        <p className="text-body text-ink2">
          {marker.clock}
          {marker.subtitle ? t('day.sheet.subPart', ', {{sub}}', { sub: marker.subtitle }) : ''}
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
          <h3 className="text-sub font-bold text-ink2">{t('day.sheet.whatShows', 'What the data shows')}</h3>
          <p className="mt-1 text-body text-ink">{marker.outcome}</p>
        </Card>

        {marker.rows.length > 0 && (
          <dl className="flex flex-col divide-y divide-line/70 rounded-card border border-line bg-card">
            {marker.rows.map((r) => (
              <div key={r.label} className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5 px-4 py-3">
                <dt className="text-sub text-ink2">{r.label}</dt>
                <dd className="num text-right text-body font-bold text-ink">{r.value}</dd>
              </div>
            ))}
          </dl>
        )}

        <p className="text-sub text-ink3">{t('day.sheet.notProof', 'Things that happen close together are not proof that one caused the other.')}</p>
        <Button variant="secondary" onClick={onClose}>
          {t('day.sheet.close', 'Close')}
        </Button>
      </div>
    </Sheet>
  )
}
