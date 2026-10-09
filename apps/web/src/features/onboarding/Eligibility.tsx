/**
 * A2 — Is this app right for you? Type 1, under 18 and pregnancy are out of scope (prd section 3): the person gets a
 * clear message and cannot continue. Only the diabetes answer is kept (yes or not sure), and only for people who continue.
 * This step is not in Damien's Stitch design; the PRD requires it.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { href } from '@/app/routeIds'
import { useBack } from '@/app/navigation'
import { Screen } from '@/ui/layout'
import { Segmented } from '@/ui/controls'
import { Alert } from '@/ui/primitives'
import { ShieldCheck } from '@/ui/icons'
import { Dock, Group, StepHead, TopBar } from './parts'
import { useOnboarding } from './useOnboarding'

type YN = 'yes' | 'no'

export function Eligibility() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const back = useBack('A1')
  const set = useOnboarding((s) => s.set)
  const [t2, setT2] = useState<'yes' | 'no' | 'unsure'>('yes')
  const [adult, setAdult] = useState<YN>('yes')
  const [pregnant, setPregnant] = useState<YN>('no')
  const out = t2 === 'no' || adult === 'no' || pregnant === 'yes'
  const yes = t('common.yes', 'Yes')
  const no = t('common.no', 'No')

  const q1 = t('onboarding.elig.t2', 'Do you have type 2 diabetes?')
  const q2 = t('onboarding.elig.adult', 'Are you 18 or older?')
  const q3 = t('onboarding.elig.pregnant', 'Are you pregnant?')

  return (
    <Screen>
      <TopBar />
      <StepHead step={2} name={t('onboarding.elig.step', 'A quick check')} title={t('onboarding.elig.title', 'Is this app right for you?')} sub={t('onboarding.elig.sub', 'Smart Health is made for adults living with type 2 diabetes.')} />
      <Group>
        <div className="flex flex-col gap-2">
          <p className="text-sub font-bold">{q1}</p>
          <Segmented label={q1} value={t2} onChange={setT2} options={[{ value: 'yes', label: yes }, { value: 'no', label: no }, { value: 'unsure', label: t('common.notSure', 'Not sure') }]} />
        </div>
        <div className="flex flex-col gap-2">
          <p className="text-sub font-bold">{q2}</p>
          <Segmented label={q2} value={adult} onChange={setAdult} options={[{ value: 'yes', label: yes }, { value: 'no', label: no }]} />
        </div>
        <div className="flex flex-col gap-2">
          <p className="text-sub font-bold">{q3}</p>
          <Segmented label={q3} value={pregnant} onChange={setPregnant} options={[{ value: 'no', label: no }, { value: 'yes', label: yes }]} />
        </div>
      </Group>
      {out ? (
        <Alert tone="info" icon={ShieldCheck} title={t('onboarding.elig.outTitle', 'Smart Health is not built for this yet')}>
          {t('onboarding.elig.out', 'It is made for adults living with type 2 diabetes. Please talk to your care team, who can support you better. You have not been enrolled.')}
        </Alert>
      ) : t2 === 'unsure' ? (
        <Alert tone="info">{t('onboarding.elig.unsure', 'If you are not sure, ask your doctor first. You can still carry on and look around.')}</Alert>
      ) : null}
      <Dock
        onBack={back}
        nextDisabled={out}
        nextLabel={t('common.continue', 'Continue')}
        onNext={() => {
          set({ hasDiabetes: t2 === 'unsure' ? 'not_sure' : 'yes' })
          navigate(`${href('A3')}?step=1`)
        }}
      />
    </Screen>
  )
}
