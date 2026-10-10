/**
 * E8 — Lunch ideas.
 *
 * Up to three options for lunch, each with the reason it is suggested: the person's own lunch with a lower measured rise, a
 * dish like their usual one but lower in salt or carbs (from the Singapore food database), or, before there is any history, a
 * general idea. Options are ideas, never instructions. Choosing one tells the learning policy it was useful.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useAcceptSuggestion, useDismissSuggestion, useLunchIdeas } from '@/data/hooks'
import { useGo } from '@/app/navigation'
import { useUi } from '@/state/store'
import type { LunchOption } from '@/data/types'
import { Header, Screen } from '@/ui/layout'
import { Alert, Button, Card, EmptyState, Skeleton, TextLink } from '@/ui/primitives'
import { CheckCircle, ForkKnife } from '@/ui/icons'


export function LunchIdeas() {
  const { t } = useTranslation()
  const SOURCE: Record<LunchOption['source'], string> = { swap: t('log.lunch.swap', 'Instead of your usual'), own: t('log.lunch.own', 'From your own meals'), general: t('log.lunch.general', 'General idea') }
  const GRADE: Record<string, string> = { lab_analysis: t('log.lunch.labAnalysed', 'lab analysed'), derived: t('log.lunch.derived', 'derived'), borrowed: t('log.lunch.borrowed', 'borrowed value'), label: t('log.lunch.labelValue', 'label value') }
  const { data, isError } = useLunchIdeas()
  const accept = useAcceptSuggestion()
  const dismiss = useDismissSuggestion()
  const go = useGo()
  const toast = useUi((s) => s.showToast)
  const [chosen, setChosen] = useState<string | null>(null)

  return (
    <Screen>
      <Header title={t('log.lunch.title', 'Lunch ideas')} back backTo="B1" sub={t('log.lunch.sub', 'Ideas that suit you. It is your choice.')} />
      {isError && <Alert tone="warn">{t('log.lunch.loadError', 'We could not load lunch ideas just now.')}</Alert>}
      {!data && !isError && <Skeleton className="h-56" />}
      {data && data.options.length === 0 && <EmptyState icon={ForkKnife}>{t('log.lunch.empty', 'No ideas yet. Log a few meals and they will appear here.')}</EmptyState>}
      {data && data.options.length > 0 && (
        <>
          <ul className="flex flex-col gap-3">
            {data.options.map((o) => (
              <li key={o.key}>
                <Card className="flex flex-col gap-2">
                  <p className="text-micro font-bold uppercase tracking-wide text-ink3">{SOURCE[o.source]}</p>
                  <p className="text-h2 font-bold leading-snug">{o.name}</p>
                  <p className="text-body text-ink2">{o.why}</p>
                  <p className="text-sub text-ink3">
                    {o.serving ? `${o.serving} · ` : ''}
                    {o.carbs != null && <>{t('log.lunch.carbs', 'about {{n}} g carbs', { n: Math.round(o.carbs) })}</>}
                    {o.sodium != null && <>{t('log.lunch.salt', ', {{n}} mg salt', { n: Math.round(o.sodium).toLocaleString('en-US') })}</>}
                    {o.grade ? ` · ${GRADE[o.grade] ?? o.grade}` : ''}
                  </p>
                  <Button
                    size="md"
                    variant={chosen === o.key ? 'secondary' : 'primary'}
                    icon={chosen === o.key ? CheckCircle : undefined}
                    disabled={accept.isPending}
                    onClick={() =>
                      accept.mutate(o.key, {
                        onSuccess: () => {
                          setChosen(o.key)
                          toast(t('log.lunch.noted', 'Noted. Enjoy your lunch, and log it when you eat.'))
                        },
                      })
                    }
                  >
                    {chosen === o.key ? t('log.lunch.chosen', 'Chosen') : t('log.lunch.haveThis', "I'll have this")}
                  </Button>
                  {chosen !== o.key && (
                    <TextLink onClick={() => dismiss.mutate(o.key, { onSuccess: () => toast(t('log.lunch.notAgain', 'Okay, we will not suggest that again.')) })} className="self-center">
                      {t('log.lunch.notForMe', 'Not for me')}
                    </TextLink>
                  )}
                </Card>
              </li>
            ))}
          </ul>
          <p className="text-sub text-ink3">
            {t('log.lunch.typical', 'Typical values for one serving from the Singapore food database, or from your own sensor and meals. Ideas only, not medical advice.')}
          </p>
          <Button variant="secondary" icon={ForkKnife} onClick={() => go('E2')}>
            {t('log.lunch.logLunch', 'Log my lunch')}
          </Button>
        </>
      )}
    </Screen>
  )
}
