/**
 * L1 — Doctor brief. Pick the period, see the key findings and alerts, and open the printable report (L3).
 * Everything shown is what the server computed for the report, so the person sees exactly what the doctor will see.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useDoctorReport } from '@/data/hooks'
import type { DoctorReport, ReportDays } from '@/data/types'
import { href } from '@/app/routeIds'
import { useGo } from '@/app/navigation'
import { Footer, Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, Skeleton, StatusPill, TextLink, type Tone } from '@/ui/primitives'
import { FilePdf, Info, ShareNetwork, Warning, WarningCircle, type IconType } from '@/ui/icons'
import { APPOINTMENT_KIND, formatWhen, useShareContext } from './shareApi'
import { ChoiceGrid } from './ChoiceGrid'

const TAG: Record<DoctorReport['alerts'][number]['priority'], { tone: Tone; icon: IconType }> = {
  urgent: { tone: 'danger', icon: WarningCircle },
  interaction: { tone: 'warn', icon: Warning },
  review: { tone: 'neutral', icon: Info },
}

export function BriefHome() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const go = useGo()
  const [days, setDays] = useState<ReportDays>(14)
  const { data, isError, isLoading } = useDoctorReport(days)
  const context = useShareContext()
  const label = { urgent: t('brief.tag.urgent', 'Urgent'), interaction: t('brief.tag.interaction', 'Interaction'), review: t('brief.tag.review', 'Review') }

  return (
    <Screen>
      <Header title={t('brief.title', 'Doctor brief')} back backTo="K1" sub={t('brief.sub', 'A report of your readings, symptoms and medicines to take to your next visit. You see exactly what your doctor sees.')} />
      <div className="md:max-w-xl">
      <ChoiceGrid
        label={t('brief.period', 'Period')}
        value={days}
        onChange={setDays}
        options={[
          { value: 7, label: t('brief.days7', '7 days') },
          { value: 14, label: t('brief.days14', '14 days') },
          { value: 30, label: t('brief.days30', '30 days') },
          { value: 90, label: t('brief.days90', '90 days') },
        ]}
      />
      </div>

      {isLoading && <Skeleton className="h-64" />}
      {isError && <Alert tone="warn">{t('brief.error', 'We could not prepare your report just now. Please try again in a moment.')}</Alert>}

      {data && (
        <>
          {/* findings and what is worth discussing on the left, the lists you add to on the right, from a laptop up */}
          <div className="grid gap-4 lg:grid-cols-2 lg:items-start lg:gap-6 [&>*]:min-w-0">
          <div className="flex flex-col gap-4">
          <Card tone="hero" as="section" className="flex flex-col gap-2">
            <p className="text-sub text-ink2">{data.period.label}</p>
            <h2 className="font-serif text-h2 font-medium tracking-tight">{t('brief.findings', 'Key findings')}</h2>
            <ul className="flex list-disc flex-col gap-1.5 pl-5 text-body">
              {data.keyFindings.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
            {data.keyFindingsSource === 'ai' && (
              <p className="rounded-card border border-line bg-card px-3 py-2 text-sub text-ink2">
                <span className="font-bold text-ink">{t('brief.aiInsight', 'AI insight.')}</span>{' '}
                {t('brief.aiNote', 'These sentences were written by an AI from the numbers in this report. The numbers come from your data. Not medical advice. Your doctor decides what they mean.')}
              </p>
            )}
            <p className="text-sub text-ink3">{t('brief.sources', 'From: {{sources}}. Sensor worn: {{wear}}.', { sources: data.sources, wear: data.cgmWear })}</p>
          </Card>

          <Card as="section" className="flex flex-col gap-3">
            <h2 className="font-serif text-h2 font-medium tracking-tight">{t('brief.worth', 'Worth discussing')}</h2>
            {data.worthDiscussing.length === 0 ? (
              <p className="text-body text-ink2">{t('brief.worthEmpty', 'Nothing stands out yet. This list fills in as you log.')}</p>
            ) : (
              <ul className="flex flex-col divide-y divide-line">
                {data.worthDiscussing.map((w, i) => (
                  <li key={i} className="flex flex-col gap-1 py-2.5 first:pt-0 last:pb-0">
                    <p className="break-words text-body">{w.text}</p>
                    <p className="break-words text-sub text-ink2">{w.evidence}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          </div>

          <div className="flex flex-col gap-4">
          <Card as="section" className="flex flex-col gap-3">
            <h2 className="font-serif text-h2 font-medium tracking-tight">{t('brief.questions', 'Questions you want to ask')}</h2>
            {context.data && context.data.questions.length > 0 ? (
              <ul className="flex list-disc flex-col gap-1.5 pl-5 text-body">
                {context.data.questions.map((q) => (
                  <li key={q.id} className="break-words">
                    {q.text}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-body text-ink2">{t('brief.noQuestions', 'You have no open questions yet. Add one from a medicine or from your care plan.')}</p>
            )}
            <div>
              <TextLink onClick={() => go('K12')}>{t('brief.openQuestions', 'Open my questions')}</TextLink>
            </div>
          </Card>

          <Card as="section" className="flex flex-col gap-2">
            <h2 className="font-serif text-h2 font-medium tracking-tight">{t('brief.nextAppointment', 'Your next appointment')}</h2>
            {context.data?.nextAppointment ? (
              <p className="text-body">
                <span className="font-bold">{APPOINTMENT_KIND[context.data.nextAppointment.kind] ?? context.data.nextAppointment.kind}</span>
                {' · '}
                {formatWhen(context.data.nextAppointment.scheduledFor)}
                {context.data.nextAppointment.location ? ` · ${context.data.nextAppointment.location}` : ''}
              </p>
            ) : (
              <p className="text-body text-ink2">{t('brief.noAppointment', 'No appointment is planned yet.')}</p>
            )}
            <div>
              <TextLink onClick={() => go('K3')}>{t('brief.openCare', 'Open my care plan')}</TextLink>
            </div>
          </Card>

          <Card as="section" className="flex flex-col gap-3">
            <h2 className="font-serif text-h2 font-medium tracking-tight">{t('brief.alerts', 'Alerts in the report')}</h2>
            {data.alerts.length === 0 ? (
              <p className="text-body text-ink2">{t('brief.noAlerts', 'No alerts were raised from your data in this period. That does not mean nothing needs attention.')}</p>
            ) : (
              <ul className="flex flex-col divide-y divide-line">
                {data.alerts.map((a, i) => (
                  <li key={i} className="flex flex-col gap-1 py-2.5 first:pt-0 last:pb-0">
                    <div>
                      <StatusPill tone={TAG[a.priority].tone} icon={TAG[a.priority].icon}>
                        {label[a.priority]}
                      </StatusPill>
                    </div>
                    <p className="break-words text-body font-bold">{a.title}</p>
                    <p className="break-words text-sub text-ink2">{a.detail}</p>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          </div>
          </div>

          <Button variant="secondary" className="md:max-w-sm" icon={ShareNetwork} onClick={() => go('L2', { sheet: { days } })}>
            {t('brief.share', 'Share with my doctor')}
          </Button>

          <Alert tone="info">{t('brief.note', 'The numbers are counts from what you and your devices recorded, worked out by fixed rules. Where the key findings say AI insight, an AI wrote the sentences from those numbers. They are for your doctor to interpret. Smart Health does not diagnose or advise on medicines.')}</Alert>
        </>
      )}

      <Footer>
        <Button className="md:mx-auto md:!w-auto md:!flex-none md:px-10" icon={FilePdf} disabled={!data} onClick={() => navigate(`${href('L3')}?days=${days}`, { state: { from: 'L1' } })}>
          {t('brief.open', 'Open the printable report')}
        </Button>
      </Footer>
    </Screen>
  )
}
