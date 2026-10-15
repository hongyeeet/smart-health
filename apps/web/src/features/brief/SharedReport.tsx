/**
 * The page a doctor opens from a share link: /s/:token. Read-only, outside the app frame, no sign-in. The token is the only key.
 * It shows the same report the person sees (ReportView), and says so at the top. A wrong, expired or turned-off link gets one plain page.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useParams } from 'react-router-dom'
import { appConfig } from '@/config/app'
import { ReportView } from '@/features/brief/ReportView'
import { FILTERS_ON, FilterBar, type ChartFilter } from '@/features/brief/PrintCharts'
import { buildExtra } from '@/features/brief/extras'
import { SharedReportError, useSharedExtras, useSharedReport } from '@/features/brief/shareApi'
import './report.css'

export function SharedReport() {
  const { t } = useTranslation()
  const { token } = useParams<{ token: string }>()
  const { data, error, isError, isLoading } = useSharedReport(token)
  const extras = useSharedExtras(token)
  const [show, setShow] = useState<Record<ChartFilter, boolean>>(FILTERS_ON)
  const gone = error instanceof SharedReportError && error.status === 404
  // the same extra sections as the printed brief (health tiles, the four charts with reasons, what the app learnt, the next visit), built from the link's own period
  const extra = extras.data ? buildExtra(t, extras.data.timeline, extras.data.learned, extras.data.nextAppointment, show) : undefined

  return (
    <div className="rp-page" style={{ position: 'fixed', inset: 0, overflowY: 'auto' }}>
      <div className="rp-bar">
        <span>{t('share.sharedFrom', 'Shared from {{name}}, read only', { name: appConfig.name })}</span>
      </div>
      {extra && <FilterBar show={show} setShow={setShow} />}
      {isLoading && <p className="rp-state">{t('share.loading', 'Loading the report…')}</p>}
      {gone && (
        <div className="rp-state">
          <h1 style={{ fontSize: 22, margin: '0 0 8px' }}>{t('share.goneTitle', 'This link has expired or was turned off.')}</h1>
          <p style={{ margin: 0 }}>{t('share.goneText', 'Ask the person who sent it for a new link.')}</p>
        </div>
      )}
      {isError && !gone && <p className="rp-state">{t('share.openFailed', 'We could not open this report just now. Please try again later.')}</p>}
      {data && <ReportView r={data} extra={extra} />}
    </div>
  )
}
