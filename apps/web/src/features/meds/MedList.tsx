import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMeds, useRemoveMed } from '@/data/hooks'
import type { Medication } from '@/data/types'
import { href } from '@/app/routeIds'
import { Header, Reveal, Screen, TileGrid } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, SectionTitle, Skeleton, StatusPill } from '@/ui/primitives'
import { Camera, CaretRight, Clock, Image as ImageIcon, Info, PencilSimple, Pill, Trash } from '@/ui/icons'
import { useLabelPicker } from '@/features/scan/useLabelPicker'
import { ClashBox } from './ClashBox'
import { fullName, refillSentence, refillSourceLine, showStrength } from './medicineText'
import { StockSection } from './StockCard'

/** H1 — Medications: three ways to add a medicine (photo, upload, type it in), and the list of what is already saved. */
export function MedList() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data, isLoading, isError, refetch } = useMeds()
  const picker = useLabelPicker()

  // Every medicine that runs low (7 days or fewer), fewest days first, each on its own line.
  const soon = (data ?? [])
    .filter((m): m is Medication & { refill: NonNullable<Medication['refill']> } => !m.asNeeded && !!m.refill && m.refill.daysLeft <= 7)
    .sort((a, b) => a.refill.daysLeft - b.refill.daysLeft)

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
          <div className="flex flex-col gap-2 md:grid md:grid-cols-2 md:gap-3 lg:grid-cols-3">
            <Button className="md:col-span-2 lg:col-span-1" icon={Camera} onClick={picker.takePhoto}>
              Take a photo
            </Button>
            <Button variant="secondary" icon={ImageIcon} onClick={picker.uploadPhoto}>
              Upload a photo
            </Button>
            <Button variant="ghost" icon={PencilSimple} onClick={() => navigate(href('H8'))}>
              Type it in by hand
            </Button>
          </div>
        </Card>
      )}
      {picker.error && (
        <Alert tone="danger" title="Could not read the label">
          {picker.error}
        </Alert>
      )}
      {picker.inputs}

      {soon.length > 0 && (
        <Alert tone="info" icon={Clock}>
          <ul className="flex flex-col gap-3">
            {soon.map((m) => (
              <li key={m.id}>
                <span className="block">{refillSentence(fullName(m), m.refill.daysLeft, t)}</span>
                {refillSourceLine(m.refillSource, t) && <span className="mt-1 block text-micro text-ink2">{refillSourceLine(m.refillSource, t)}</span>}
              </li>
            ))}
          </ul>
        </Alert>
      )}

      <ClashBox />

      <StockSection />

      <SectionTitle>Your medicines</SectionTitle>
      {isLoading && <Skeleton className="h-40" />}
      {isError && (
        <Alert tone="warn" onClick={() => void refetch()}>
          We could not load your medicines. Tap to try again.
        </Alert>
      )}
      {data && data.length === 0 && <EmptyState icon={Pill}>No medicines yet. Add your first one above.</EmptyState>}
      {data && data.length > 0 && (
        <TileGrid spread cols={2}>
          {data.map((m, i) => (
            <li key={m.id}>
              <Reveal id={`med-${m.id}`} i={i} className="h-full">
                <MedCard m={m} onOpen={() => navigate(href('H6', { id: m.id }))} />
              </Reveal>
            </li>
          ))}
        </TileGrid>
      )}
    </Screen>
  )
}

function MedCard({ m, onOpen }: { m: Medication; onOpen: () => void }) {
  const remove = useRemoveMed()
  const [confirming, setConfirming] = useState(false)
  return (
    <div className="relative flex h-full flex-col">
      <Card className="flex flex-1 flex-col gap-3" onClick={onOpen}>
        <MedCardBody m={m} />
      </Card>
      {/* A sibling of the card, not inside it, because a button cannot sit inside another button. */}
      <button
        type="button"
        onClick={() => setConfirming(true)}
        aria-label={`Remove ${fullName(m)}`}
        className="press absolute right-3 top-3 flex min-h-12 items-center gap-1.5 rounded-chip px-3 text-sub font-bold text-ink2 hover:bg-well"
      >
        <Trash size={18} aria-hidden /> Remove
      </button>
      {confirming && (
        <div className="mt-2 flex flex-col gap-3 rounded-card border border-line bg-card p-4" role="alertdialog" aria-label={`Remove ${fullName(m)}?`}>
          <p className="text-body">
            Remove <b>{fullName(m)}</b> from your list? It will stop showing in your medicines, doses and clash checks. Your past dose history is kept.
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
      <p className="mt-auto flex items-center gap-1 text-sub font-bold text-brand">
        What it is for and side effects
        <CaretRight size={16} aria-hidden />
      </p>
    </>
  )
}
