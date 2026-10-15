import type { MarkerPick } from '@/charts/DayChart'
import { clock, signed } from '@/lib/format'
import { useGo } from '@/app/navigation'
import { Sheet } from '@/ui/Sheet'
import { Button, EstimateBadge, StatusPill, type Tone } from '@/ui/primitives'

const doseTone: Record<string, { tone: Tone; label: string }> = {
  taken: { tone: 'ok', label: 'Taken' },
  taken_late_logged: { tone: 'ok', label: 'Taken, logged late' },
  unconfirmed: { tone: 'warn', label: 'Not confirmed' },
  missed: { tone: 'danger', label: 'Missed' },
  due: { tone: 'info', label: 'Due now' },
}

export function MarkerSheet({ onClose, pick, dayLabel }: { onClose: () => void; pick?: MarkerPick; dayLabel?: string }) {
  const go = useGo()
  if (!pick) return null
  const title = { meal: 'Meal', dose: 'Medicines', workout: 'Workout', symptom: 'Symptom' }[pick.type]
  return (
    <Sheet title={title} onClose={onClose}>
      <div className="flex flex-col gap-4">
        <p className="text-sub text-ink2">{dayLabel}</p>
        {pick.type === 'meal' &&
          pick.items.map((m) => (
            <div key={m.id} className="flex flex-col gap-3">
              <div>
                <p className="text-h2 font-bold">{m.name}</p>
                <p className="text-sub text-ink2">{clock(m.t)}</p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-body">{m.carbsG} g carbs</span>
                {m.estimated && <EstimateBadge />}
                {m.flags.includes('high_salt') && <StatusPill tone="warn">High salt</StatusPill>}
                {m.flags.includes('high_sugar') && <StatusPill tone="warn">High sugar</StatusPill>}
              </div>
              {m.rise != null ? (
                <div className="rounded-card bg-well p-3.5">
                  <p className="text-body">
                    2 hours after this meal your glucose rose <span className="num text-h2">{signed(m.rise)}</span> mmol/L{m.rise >= 3 ? ', more than your usual for this kind of meal' : m.rise <= 1.6 ? ', gentler than most of your meals' : ''}.
                  </p>
                  <p className="mt-1 text-sub text-ink3">The rise comes from your glucose sensor. The nutrients are estimates until you confirm them.</p>
                </div>
              ) : (
                <p className="rounded-card bg-well p-3.5 text-body">The rise will show here about 2 hours after the meal, from your sensor.</p>
              )}
            </div>
          ))}
        {pick.type === 'dose' &&
          pick.items.map((d) => {
            const s = doseTone[d.status] ?? doseTone.taken!
            return (
              <div key={d.id} className="flex items-center justify-between gap-3 border-b border-line pb-3 last:border-0">
                <div>
                  <p className="text-body font-bold">{d.name}</p>
                  <p className="text-sub text-ink2">{clock(d.t)}</p>
                </div>
                <StatusPill tone={s.tone}>{s.label}</StatusPill>
              </div>
            )
          })}
        {pick.type === 'workout' &&
          pick.items.map((w) => (
            <div key={w.id} className="flex flex-col gap-3">
              <p className="text-h2 font-bold">{w.label}</p>
              <p className="text-body">
                {clock(w.t)}, {w.minutes} minutes, {w.intensity}
              </p>
              {w.glucoseChange2h != null && (
                <div className="rounded-card bg-well p-3.5">
                  <p className="text-body">
                    In the 2 hours after, your glucose changed by <span className="num text-h2">{signed(w.glucoseChange2h)}</span> mmol/L.
                  </p>
                  <p className="mt-1 text-sub text-ink3">Associated with, not proven.</p>
                </div>
              )}
            </div>
          ))}
        {pick.type === 'symptom' &&
          pick.items.map((s) => (
            <div key={s.id} className="flex flex-col gap-2">
              <p className="text-h2 font-bold">{s.label}</p>
              <p className="text-body">
                {clock(s.t)}, strength {s.severity} of 5
              </p>
              <p className="text-sub text-ink2">This is included in your doctor brief. Your doctor sees what you see.</p>
            </div>
          ))}
        <Button variant="secondary" onClick={() => { onClose(); go('C2') }}>
          Open glucose insights
        </Button>
      </div>
    </Sheet>
  )
}
