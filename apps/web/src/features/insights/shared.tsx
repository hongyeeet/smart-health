/**
 * What every Insights screen has in common: the title, the tab strip (C1 to C6), the period switch (7 / 30 / 90 days) and the
 * loading, error and empty states. The period is kept in one place so it stays when the person moves between tabs.
 */
import type { ReactNode } from 'react'
import { useTranslation } from 'react-i18next'
import { create } from 'zustand'
import type { InsightsDays, InsightsPattern, InsightsPeriod, InsightsTab } from '@/data/types'
import type { RouteId } from '@/app/routeIds'
import { useGo } from '@/app/navigation'
import { Header, Screen } from '@/ui/layout'
import { Segmented, TabStrip } from '@/ui/controls'
import { Alert, Card, EmptyState, SectionTitle, Skeleton, UnverifiedTag } from '@/ui/primitives'
import { ChartLineUp, Info } from '@/ui/icons'

export type WhyTopic = 'week' | 'glucose' | 'food' | 'activity' | 'sleep' | 'medication' | 'findings' | 'sprint'

export const useInsightsDays = create<{ days: InsightsDays; setDays: (d: InsightsDays) => void }>((set) => ({ days: 30, setDays: (days) => set({ days }) }))

export function InsightsFrame({ tab, period, children, back }: { tab: RouteId; period?: InsightsPeriod; children: ReactNode; back?: RouteId }) {
  const go = useGo()
  const { days, setDays } = useInsightsDays()
  const { t } = useTranslation()
  const tabs: { value: RouteId; label: string }[] = [
    { value: 'C1', label: t('insights.shared.tabOverview', 'Overview') },
    { value: 'C2', label: t('insights.shared.tabGlucose', 'Glucose') },
    { value: 'C3', label: t('insights.shared.tabFood', 'Food') },
    { value: 'C4', label: t('insights.shared.tabActivity', 'Activity') },
    { value: 'C5', label: t('insights.shared.tabSleep', 'Sleep and stress') },
    { value: 'C6', label: t('insights.shared.tabMedication', 'Medication') },
  ]
  return (
    <Screen tabs>
      <Header title={t('insights.shared.title', 'Insights')} back={!!back} backTo={back} />
      <TabStrip label={t('insights.shared.tabsLabel', 'Insights sections')} tabs={tabs} value={tab} onChange={(v) => go(v)} />
      <Segmented
        label={t('insights.shared.period', 'Period')}
        value={days}
        onChange={setDays}
        options={[
          { value: 7, label: t('insights.shared.days', '{{n}} days', { n: 7 }) },
          { value: 30, label: t('insights.shared.days', '{{n}} days', { n: 30 }) },
          { value: 90, label: t('insights.shared.days', '{{n}} days', { n: 90 }) },
        ]}
      />
      {period && <p className="-mt-1 text-sub text-ink3">{period.label}</p>}
      {children}
    </Screen>
  )
}

/** Loading, error and "nothing yet" for a query. Renders `children` only when there is data to show. */
export function Gate({ data, isError, empty, emptyText, children }: { data: unknown; isError: boolean; empty: boolean; emptyText: string; children: ReactNode }) {
  const { t } = useTranslation()
  if (isError) return <Alert tone="warn">{t('insights.shared.loadError', 'We could not load this just now. Please try again in a moment.')}</Alert>
  if (!data) return <Skeleton className="h-64" />
  if (empty) return <EmptyState icon={ChartLineUp}>{emptyText}</EmptyState>
  return <>{children}</>
}

/** The plain sentence that goes above a chart, with the "Why am I seeing this?" link under it. */
export function Plain({ children, why }: { children: ReactNode; why: WhyTopic }) {
  const go = useGo()
  const { t } = useTranslation()
  return (
    <div className="flex flex-col gap-1">
      <p className="text-body text-ink">{children}</p>
      <button type="button" onClick={() => go('C7', { sheet: { topic: why } })} className="press -ml-1 flex min-h-11 items-center gap-1.5 self-start rounded-chip px-1 text-sub font-bold text-brand">
        <Info size={18} aria-hidden /> {t('insights.shared.whyLink', 'Why am I seeing this?')}
      </button>
    </div>
  )
}

/** Findings from the person's own history. Always labelled unverified: they compare two things, they do not prove a cause. */
export function Findings({ items, onOpen }: { items: InsightsPattern[]; onOpen?: (to: InsightsTab) => void }) {
  const go = useGo()
  const { t } = useTranslation()
  if (!items.length) return null
  return (
    <section className="flex flex-col gap-2">
      <SectionTitle>{t('insights.shared.findings', 'What your history shows')}</SectionTitle>
      {items.map((p) => (
        <Card key={p.key} className="flex flex-col gap-2">
          <p className="text-body">{p.text}</p>
          <p className="num text-sub text-ink3">{t('insights.shared.basedOn', 'Based on {{n}} matched events in your own history.', { n: p.n })}</p>
          <div className="flex flex-wrap items-center gap-2">
            <UnverifiedTag />
            <button type="button" onClick={() => (onOpen ? onOpen(p.to) : go('C7', { sheet: { topic: 'findings' } }))} className="press min-h-11 rounded-chip px-2 text-sub font-bold text-brand">
              {onOpen ? t('insights.shared.seeMore', 'See more') : t('insights.shared.whyLink', 'Why am I seeing this?')}
            </button>
          </div>
        </Card>
      ))}
    </section>
  )
}

export const num = (n: number | null | undefined, digits = 0) => (n == null ? '–' : n.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits }))

export function Tile({ label, value, unit, sub }: { label: string; value: string; unit?: string; sub?: string }) {
  return (
    <div className="flex flex-col gap-0.5 rounded-card border border-line bg-card p-3">
      <span className="text-sub text-ink2">{label}</span>
      <span className="num text-xl leading-tight">
        {value}
        {unit && <span className="ml-1 text-sub text-ink3">{unit}</span>}
      </span>
      {sub && <span className="text-micro text-ink3">{sub}</span>}
    </div>
  )
}
