import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMeds, useRemoveMed } from '@/data/hooks'
import type { Medication } from '@/data/types'
import { href } from '@/app/routeIds'
import { Header, Reveal, Screen } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, SectionTitle, Skeleton, StatusPill } from '@/ui/primitives'
import { Camera, CaretRight, Clock, Image as ImageIcon, Info, PencilSimple, Pill, Trash } from '@/ui/icons'
import { useLabelPicker } from '@/features/scan/useLabelPicker'
import { ClashBox } from './ClashBox'

/** H1 — Medications: three ways to add a medicine (photo, upload, type it in), and the list of what is already saved. */
export function MedList() {
  const navigate = useNavigate()
  const { data, isLoading, isError, refetch } = useMeds()
  const picker = useLabelPicker()

  const soon = data?.find((m) => m.refill && m.refill.daysLeft <= 7)

  return (
    <Screen tabs>
      <Header title="Medications" sub="Add a medicine by photo or by typing it in. Dose times come from your own label." />

      {picker.busy ? (
        <Card tone="soft" className="flex flex-col items-center gap-3 py-8">
          <Skeleton className="h-24 w-full" />
          <p className="text-body font-bold text-ink2">Reading your label…</p>
          <p className="text-sub text-ink3">This takes a few seconds.</p>
        </Card>
      ) : (
        <Card className="flex flex-col gap-2">
          <SectionTitle>Add a medicine</SectionTitle>
          <Button icon={Camera} onClick={picker.takePhoto}>
            Take a photo
          </Button>
          <Button variant="secondary" icon={ImageIcon} onClick={picker.uploadPhoto}>
            Upload a photo
          </Button>
          <Button variant="ghost" icon={PencilSimple} onClick={() => navigate(href('H8'))}>
            Type it in by hand
          </Button>
        </Card>
      )}
      {picker.error && (
        <Alert tone="danger" title="Could not read the label">
          {picker.error}
        </Alert>
      )}
      {picker.inputs}

      {soon?.refill && (
        <Alert tone="info" icon={Clock}>
          {soon.refill.daysLeft === 0
            ? `${soon.name} may have run out. You may want to arrange a refill.`
            : `${soon.name} may run out in about ${soon.refill.daysLeft} ${soon.refill.daysLeft === 1 ? 'day' : 'days'}. You may want to arrange a refill.`}
        </Alert>
      )}

      <ClashBox />

      <SectionTitle>Your medicines</SectionTitle>
      {isLoading && <Skeleton className="h-40" />}
      {isError && (
        <Alert tone="warn" onClick={() => void refetch()}>
          We could not load your medicines. Tap to try again.
        </Alert>
      )}
      {data && data.length === 0 && <EmptyState icon={Pill}>No medicines yet. Add your first one above.</EmptyState>}
      {data && data.length > 0 && (
        <ul className="flex flex-col gap-3">
          {data.map((m, i) => (
            <li key={m.id}>
              <Reveal id={`med-${m.id}`} i={i}>
                <MedCard m={m} onOpen={() => navigate(href('H6', { id: m.id }))} />
              </Reveal>
            </li>
          ))}
        </ul>
      )}
    </Screen>
  )
}

/** The strength is shown beside the name unless it was never entered or the name already says it ("Amlodipine 5 mg"). */
const showStrength = (m: Medication) =>
  !!m.strength && m.strength !== 'Strength not entered' && !m.name.toLowerCase().replace(/\s+/g, '').includes(m.strength.toLowerCase().replace(/\s+/g, ''))

function MedCard({ m, onOpen }: { m: Medication; onOpen: () => void }) {
  const remove = useRemoveMed()
  const [confirming, setConfirming] = useState(false)
  return (
    <div className="relative">
      <Card className="flex flex-col gap-3" onClick={onOpen}>
        <MedCardBody m={m} />
      </Card>
      {/* A sibling of the card, not inside it, because a button cannot sit inside another button. */}
      <button
        type="button"
        onClick={() => setConfirming(true)}
        aria-label={`Remove ${m.name}`}
        className="press absolute right-3 top-3 flex min-h-10 items-center gap-1.5 rounded-chip px-3 text-sub font-bold text-ink2 hover:bg-well"
      >
        <Trash size={18} aria-hidden /> Remove
      </button>
      {confirming && (
        <div className="mt-2 flex flex-col gap-3 rounded-card border border-line bg-card p-4" role="alertdialog" aria-label={`Remove ${m.name}?`}>
          <p className="text-body">
            Remove <b>{m.name}</b> from your list? It will stop showing in your medicines, doses and clash checks. Your past dose history is kept.
          </p>
          <div className="flex flex-wrap gap-2">
            <Button size="md" variant="danger" className="!w-auto" disabled={remove.isPending} onClick={() => remove.mutate(m.id, { onSuccess: () => setConfirming(false) })}>
              {remove.isPending ? 'Removing…' : 'Yes, remove it'}
            </Button>
            <Button size="md" variant="ghost" className="!w-auto" disabled={remove.isPending} onClick={() => setConfirming(false)}>
              Keep it
            </Button>
          </div>
          {remove.isError && <p className="text-sub text-ink2">We could not remove it just now. Please try again.</p>}
        </div>
      )}
    </div>
  )
}

function MedCardBody({ m }: { m: Medication }) {
  return (
    <>
      <div className="min-w-0 pr-24">
        <p className="break-words text-h2 font-bold leading-tight">
          {m.name}
          {showStrength(m) && <span className="font-normal text-ink2"> {m.strength}</span>}
        </p>
        <p className="text-sub text-ink2">
          {m.asNeeded ? 'Only when needed' : m.times.length ? m.times.join(', ') : 'No dose times'}
          {m.withFood && ', with food'}
        </p>
      </div>
      {(m.kind !== 'prescription' || m.badge) && (
        <div className="flex flex-wrap gap-2">
          {m.kind === 'supplement' && (
            <StatusPill tone="neutral" icon={Pill} bare>
              Supplement
            </StatusPill>
          )}
          {m.kind === 'tcm' && (
            <StatusPill tone="neutral" icon={Pill} bare>
              Herbal
            </StatusPill>
          )}
          {m.kind === 'otc' && (
            <StatusPill tone="neutral" icon={Pill} bare>
              Over the counter
            </StatusPill>
          )}
          {m.badge === 'not_checked' && (
            <StatusPill tone="neutral" icon={Info}>
              Not checked
            </StatusPill>
          )}
        </div>
      )}
      <p className="flex items-center gap-1 text-sub font-bold text-brand">
        What it is for and side effects
        <CaretRight size={16} aria-hidden />
      </p>
    </>
  )
}
