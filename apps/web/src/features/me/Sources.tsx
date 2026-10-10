/**
 * K4. Connected sources: which devices and feeds this person's data comes from, and how recent the last data is.
 * Read only. There are no connect or disconnect flows yet, so a source that is not connected says so and nothing more.
 */
import { useGo } from '@/app/navigation'
import { Header, Screen } from '@/ui/layout'
import { Alert, Card, EmptyState, StatusPill, TextLink, Skeleton, type Tone } from '@/ui/primitives'
import { Camera, CheckCircle, Clock, Drop, LinkBreak, Watch, type IconType } from '@/ui/icons'
import { useConnectedSources, type ConnectedSource } from './care/api'

const ICON: Record<ConnectedSource['key'], IconType> = { cgm: Drop, watch: Watch, camera: Camera }

const STATUS: Record<ConnectedSource['status'], { tone: Tone; icon: IconType }> = {
  connected: { tone: 'ok', icon: CheckCircle },
  connected_no_data: { tone: 'neutral', icon: Clock },
  not_connected: { tone: 'neutral', icon: LinkBreak },
  on_device: { tone: 'brand', icon: Camera },
}

export function Sources() {
  const go = useGo()
  const { data, isError, isLoading } = useConnectedSources()
  const sensorConnected = data?.some((s) => s.key === 'cgm' && (s.status === 'connected' || s.status === 'connected_no_data'))

  return (
    <Screen>
      <Header title="Connected sources" back backTo="K1" sub="Where your data comes from, and how recent the last data is." />

      {isError && <Alert tone="warn">We could not load your sources just now. Please try again in a moment.</Alert>}
      {isLoading && !data && <Skeleton className="h-64" />}
      {data && data.length === 0 && <EmptyState icon={LinkBreak}>No sources yet.</EmptyState>}

      {data && data.length > 0 && (
        <ul className="flex flex-col gap-3">
          {data.map((s) => {
            const Icon = ICON[s.key]
            const st = STATUS[s.status]
            return (
              <li key={s.key}>
                <Card className="flex flex-col gap-3">
                  <div className="flex items-start gap-3">
                    <span className="flex h-12 w-12 flex-none items-center justify-center rounded-full bg-brand-soft text-brand">
                      <Icon size={24} aria-hidden />
                    </span>
                    <div className="min-w-0 flex-1">
                      <span className="block text-body font-bold">{s.label}</span>
                      {s.model && <span className="block text-sub text-ink2">{s.model}</span>}
                    </div>
                  </div>
                  <StatusPill tone={st.tone} icon={st.icon}>
                    {s.statusLabel}
                  </StatusPill>
                  <p className="text-sub text-ink2">{s.note}</p>
                </Card>
              </li>
            )
          })}
        </ul>
      )}

      {sensorConnected && <TextLink onClick={() => go('C8')}>Glucose sensor sprint</TextLink>}
    </Screen>
  )
}
