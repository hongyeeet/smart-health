import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMeds, useStock } from '@/data/hooks'
import type { Medication } from '@/data/types'
import { href } from '@/app/routeIds'
import { useUi } from '@/state/store'
import { Header, Reveal, Screen, TileGrid } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, SectionTitle, Skeleton } from '@/ui/primitives'
import { Camera, Image as ImageIcon, PencilSimple, Pill } from '@/ui/icons'
import { useLabelPicker } from '@/features/scan/useLabelPicker'
import { ClashBox } from './ClashBox'
import { MedStockCard } from './MedStockCard'
import { RefillNotice } from './RefillNotice'
import { UserSwitch } from '@/features/home/UserSwitch'

/** H1 — Medications: three ways to add a medicine (photo, upload, type it in), the notices, and "All medications": every medicine with how many are left. */
export function MedList() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { data, isLoading, isError, refetch } = useMeds()
  const { data: stock } = useStock()
  const picker = useLabelPicker()
  const openSheet = useUi((s) => s.openSheet)
  const stockOf = new Map((stock?.ready ? stock.items : []).map((s) => [s.id, s]))
  const today = new Date().toLocaleDateString('sv-SE')

  // Every medicine that runs low (7 days or fewer), fewest days first, one notice each. A course that has ended has nothing to run out.
  const soon = (data ?? [])
    .filter((m): m is Medication & { refill: NonNullable<Medication['refill']> } => !m.asNeeded && !!m.refill && m.refill.daysLeft <= 7)
    .sort((a, b) => a.refill.daysLeft - b.refill.daysLeft)

  return (
    <Screen tabs>
      <Header title="Medications" sub="Add a medicine by photo or by typing it in. Dose times come from your own label." trailing={<UserSwitch />} />

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

      {soon.map((m) => (
        <RefillNotice key={m.id} m={m} />
      ))}

      <ClashBox />

      <section className="flex flex-col gap-3">
        <SectionTitle>{t('meds.allTitle', 'All medications')}</SectionTitle>
        <p className="-mt-2 text-sub text-ink2">{t('meds.allIntro', 'How many you have left goes down by one dose each time you mark a dose as taken.')}</p>
        {isLoading && <Skeleton className="h-40" />}
        {isError && (
          <Alert tone="warn" onClick={() => void refetch()}>
            We could not load your medicines. Tap to try again.
          </Alert>
        )}
        {data && data.length === 0 && <EmptyState icon={Pill}>No medicines yet. Add your first one above.</EmptyState>}
        {data && data.length > 0 && (
          <TileGrid spread>
            {data.map((m, i) => (
              <li key={m.id}>
                <Reveal id={`med-${m.id}`} i={i} className="h-full">
                  <MedStockCard
                    m={m}
                    stock={stockOf.get(m.id)}
                    today={today}
                    onBought={() => openSheet('H9', { medId: m.id, mode: 'add' })}
                    onEdit={() => openSheet('H9', { medId: m.id, mode: 'set' })}
                    onOpen={() => navigate(href('H6', { id: m.id }))}
                  />
                </Reveal>
              </li>
            ))}
          </TileGrid>
        )}
      </section>
    </Screen>
  )
}
