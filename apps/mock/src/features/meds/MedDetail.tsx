import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useAddQuestion, useMed } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import { Header, Screen } from '@/ui/layout'
import { Segmented } from '@/ui/controls'
import { Alert, Button, Card, SectionTitle, Skeleton, SourceTag, StatusPill } from '@/ui/primitives'
import { Clock, Info, SpeakerHigh } from '@/ui/icons'

export function MedDetail() {
  const { id = 'metformin' } = useParams()
  const { data: m } = useMed(id)
  const { t, i18n } = useTranslation()
  const [lang, setLang] = useState<'en' | 'zh'>('en')
  const toast = useUi((s) => s.showToast)
  const add = useAddQuestion()
  const go = useGo()
  if (!m)
    return (
      <Screen>
        <Header title="Medicine" back backTo="H1" />
        <Skeleton className="h-60" />
      </Screen>
    )
  const hasZh = id === 'metformin'
  const L = hasZh ? lang : 'en'
  const tr = (key: string, fallback: string): string => (L === 'zh' ? t(key, { lng: 'zh', defaultValue: fallback }) : fallback)
  const sideEffects = L === 'zh' && hasZh ? (i18n.getResource('zh', 'translation', 'med.metformin.side') as string[]) : m.sideEffects
  const howLabel = m.times.length ? `${m.strength}, ${m.times.length === 1 ? 'once' : m.times.length === 2 ? 'twice' : m.times.length + ' times'} a day at ${m.times.join(' and ')}${m.withFood ? ', with food' : ''}.` : 'No dose times set. Ask your pharmacist how to take it.'

  return (
    <Screen>
      <Header title={m.name} back backTo="H1" sub={m.strength} />
      {hasZh && <Segmented label="Language" value={lang} onChange={setLang} options={[{ value: 'en', label: 'English' }, { value: 'zh', label: '中文' }]} />}
      <Button variant="secondary" icon={SpeakerHigh} onClick={() => toast(L === 'zh' ? '正在朗读（演示）' : 'Playing audio (prototype)')}>
        {tr('med.listen', 'Listen')}
      </Button>

      <Card className="flex flex-col gap-1.5">
        <SectionTitle>{tr('med.for', 'What it is for')}</SectionTitle>
        <p className="text-body">{hasZh ? tr('med.metformin.purpose', m.purpose) : m.purpose}</p>
      </Card>
      <Card className="flex flex-col gap-1.5">
        <SectionTitle>{tr('med.how', 'How you take it (from your own label)')}</SectionTitle>
        <p className="text-body">{hasZh ? tr('med.metformin.how', howLabel) : howLabel}</p>
      </Card>
      {sideEffects.length > 0 && (
        <Card className="flex flex-col gap-1.5">
          <SectionTitle>{tr('med.side', 'Common side effects')}</SectionTitle>
          <ul className="flex flex-col gap-1.5">
            {sideEffects.map((s) => (
              <li key={s} className="flex gap-3 text-body">
                <span className="mt-2.5 h-1.5 w-1.5 flex-none rounded-full bg-brand" aria-hidden />
                {s}
              </li>
            ))}
          </ul>
        </Card>
      )}
      <Card className="flex flex-col gap-1.5">
        <SectionTitle>{tr('med.tell', 'When to tell your doctor')}</SectionTitle>
        <p className="text-body">{hasZh ? tr('med.metformin.tell', 'Tell your doctor or pharmacist if you have lasting vomiting, bad stomach upset, or you are unsure whether to take a dose.') : 'Tell your doctor or pharmacist about any side effect that worries you, or if you are unsure whether to take a dose.'}</p>
      </Card>

      {m.refill && (
        <Alert tone="info" icon={Clock} title={`Runs out in about ${m.refill.daysLeft} days`}>
          {m.refill.unitsLeft} tablets left at your current pace. We remind you 7 days ahead.
        </Alert>
      )}

      <div className="flex flex-col gap-2">
        <SourceTag>{tr('med.source', 'your label and a drug information dataset. This is not medical advice.')}</SourceTag>
        <StatusPill tone="info" icon={Info}>Not an authoritative drug label</StatusPill>
      </div>

      <Button
        variant="secondary"
        onClick={() =>
          add.mutate({ text: `A question about ${m.name} ${m.strength}: `, origin: 'user' }, { onSuccess: () => { toast('Added to your doctor questions'); go('K3') } })
        }
      >
        Add a question for my doctor
      </Button>
    </Screen>
  )
}
