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
import { Footer, Header, Screen } from '@/ui/layout'
import { Segmented } from '@/ui/controls'
import { Alert, Button, Card, Skeleton, StatusPill, type Tone } from '@/ui/primitives'
import { FilePdf, Info, Warning, WarningCircle, type IconType } from '@/ui/icons'

const TAG: Record<DoctorReport['alerts'][number]['priority'], { tone: Tone; icon: IconType }> = {
  urgent: { tone: 'danger', icon: WarningCircle },
  interaction: { tone: 'warn', icon: Warning },
  review: { tone: 'neutral', icon: Info },
}

export function BriefHome() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [days, setDays] = useState<ReportDays>(14)
  const { data, isError, isLoading } = useDoctorReport(days)
  const label = { urgent: t('brief.tag.urgent', 'Urgent'), interaction: t('brief.tag.interaction', 'Interaction'), review: t('brief.tag.review', 'Review') }

  return (
    <Screen>
      <Header title={t('brief.title', 'Doctor brief')} back backTo="K1" sub={t('brief.sub', 'A report of your readings, symptoms and medicines to take to your next visit. You see exactly what your doctor sees.')} />
      <Segmented
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

      {isLoading && <Skeleton className="h-64" />}
      {isError && <Alert tone="warn">{t('brief.error', 'We could not prepare your report just now. Please try again in a moment.')}</Alert>}

      {data && (
        <>
          <Card tone="hero" as="section" className="flex flex-col gap-2">
            <p className="text-sub text-ink2">{data.period.label}</p>
            <h2 className="font-serif text-h2 font-medium tracking-tight">{t('brief.findings', 'Key findings')}</h2>
            <ul className="flex list-disc flex-col gap-1.5 pl-5 text-body">
              {data.keyFindings.map((f) => (
                <li key={f}>{f}</li>
              ))}
            </ul>
            <p className="text-sub text-ink3">{t('brief.sources', 'From: {{sources}}. Sensor worn: {{wear}}.', { sources: data.sources, wear: data.cgmWear })}</p>
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

          <Alert tone="info">{t('brief.note', 'These are counts from what you and your devices recorded, worked out by fixed rules, not by AI. They are for your doctor to interpret. Smart Health does not diagnose or advise on medicines.')}</Alert>
        </>
      )}

      <Footer>
        <Button icon={FilePdf} disabled={!data} onClick={() => navigate(`${href('L3')}?days=${days}`)}>
          {t('brief.open', 'Open the printable report')}
        </Button>
      </Footer>
    </Screen>
  )
}
