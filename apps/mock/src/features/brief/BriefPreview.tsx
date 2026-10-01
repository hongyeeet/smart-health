import { useBrief } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { href } from '@/app/routeIds'
import { Header, Footer, Screen } from '@/ui/layout'
import { Alert, Button, Card, SectionTitle, Skeleton, StatusPill } from '@/ui/primitives'
import { Download, FilePdf, ShareNetwork, ShieldCheck } from '@/ui/icons'

const sections = ['Top 3 to discuss', 'Medication and adherence', 'Glucose', 'Nutrition', 'Exercise', 'Sleep and stress', 'Three day traces', 'Patterns for clinician review', 'Symptoms', 'Preventive care', 'Your own questions', 'Data completeness']

export function BriefPreview() {
  const { data } = useBrief()
  const go = useGo()
  const toast = useUi((s) => s.showToast)
  if (!data)
    return (
      <Screen>
        <Header title="Doctor brief" back backTo="K1" />
        <Skeleton className="h-72" />
      </Screen>
    )
  return (
    <Screen>
      <Header title="Doctor brief" back backTo="K1" sub={`Covers ${data.period}`} />
      <Card tone="hero" className="flex flex-col gap-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-sub text-ink3">Patient</p>
            <p className="num text-xl">
              {data.initials}, born {data.birthYear}
            </p>
          </div>
          <FilePdf size={36} className="text-brand" aria-hidden />
        </div>
        <div className="flex flex-col gap-2">
          <p className="text-sub font-bold text-ink2">Data completeness</p>
          {data.completeness.map((c) => (
            <div key={c.stream} className="flex items-center gap-3 text-sub">
              <span className="w-32 flex-none">{c.stream}</span>
              <span className="h-2.5 flex-1 overflow-hidden rounded-full bg-well" aria-hidden>
                <span className="block h-full rounded-full bg-brand" style={{ width: `${c.pct}%` }} />
              </span>
              <span className="num w-10 text-right text-body">{c.pct}%</span>
            </div>
          ))}
        </div>
      </Card>

      <section className="flex flex-col gap-3">
        <SectionTitle>Top 3 to discuss</SectionTitle>
        <ol className="flex flex-col gap-3">
          {data.top3.map((t, i) => (
            <li key={t.id} className="flex gap-3 rounded-card border border-line bg-card p-3.5">
              <span className="num flex h-9 w-9 flex-none items-center justify-center rounded-full bg-brand text-h2 text-on-brand">{i + 1}</span>
              <span>
                <span className="block text-body">{t.text}</span>
                <span className="mt-1 block text-sub text-ink3">{t.evidence}</span>
              </span>
            </li>
          ))}
        </ol>
      </section>

      <Card tone="soft" className="flex flex-col gap-2">
        <p className="text-sub font-bold">What is inside</p>
        <ul className="grid grid-cols-1 gap-1 text-body">
          {sections.map((s, i) => (
            <li key={s} className="flex gap-2">
              <span className="num w-6 text-ink3">{i + 1}</span>
              {s}
            </li>
          ))}
        </ul>
      </Card>

      <Alert tone="info" icon={ShieldCheck}>
        Your doctor sees exactly what you see. Numbers are computed, not written by AI. Patterns are labelled unverified.
      </Alert>
      <StatusPill tone="neutral">Written sentences each point to their evidence.</StatusPill>

      <Footer>
        <Button icon={ShareNetwork} onClick={() => go('L2')}>
          Share with my doctor
        </Button>
        <Button variant="secondary" icon={Download} onClick={() => toast('Download is part of the real app. Open the A4 page to print.')}>
          Download
        </Button>
        <Button variant="ghost" onClick={() => window.open(href('L3'), '_blank')}>
          Open the A4 page
        </Button>
      </Footer>
    </Screen>
  )
}
