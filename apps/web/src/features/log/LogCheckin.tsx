/**
 * E5 — Mood and sleep check-in.
 *
 * Four Rating components (mood, stress, sleep quality, energy), each 1–5.
 * Saves via useFinishLog → E6.
 */
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useFinishLog } from './useFinishLog'
import { Header, Footer, Screen } from '@/ui/layout'
import { Rating } from '@/ui/controls'
import { Alert, Button } from '@/ui/primitives'

export function LogCheckin() {
  const { t } = useTranslation()
  const [mood, setMood] = useState(3)
  const [stress, setStress] = useState(4)
  const [sleep, setSleep] = useState(2)
  const [energy, setEnergy] = useState(3)
  const { save, pending, error } = useFinishLog()
  return (
    <Screen>
      <Header title={t('log.checkin.title', 'Mood and sleep')} back backTo="E1" sub={t('log.checkin.sub', 'Thirty seconds. Tap a number for each.')} />
      <Rating label={t('log.checkin.mood', 'Mood')} value={mood} onChange={setMood} lowLabel={t('log.checkin.moodLow', 'Very low')} highLabel={t('log.checkin.moodHigh', 'Very good')} />
      <Rating label={t('log.checkin.stress', 'Stress')} value={stress} onChange={setStress} lowLabel={t('log.checkin.stressLow', 'Calm')} highLabel={t('log.checkin.stressHigh', 'Very stressed')} />
      <Rating label={t('log.checkin.sleep', 'Sleep quality')} value={sleep} onChange={setSleep} lowLabel={t('log.checkin.sleepLow', 'Very poor')} highLabel={t('log.checkin.sleepHigh', 'Excellent')} />
      <Rating label={t('log.checkin.energy', 'Energy')} value={energy} onChange={setEnergy} lowLabel={t('log.checkin.energyLow', 'Exhausted')} highLabel={t('log.checkin.energyHigh', 'Energised')} />
      {error && <Alert tone="danger">{error}</Alert>}
      <Footer>
        <Button disabled={pending} onClick={() => save({ kind: 'checkin', mood, stress, sleep, energy })}>
          {t('log.checkin.save', 'Save check-in')}
        </Button>
      </Footer>
    </Screen>
  )
}
