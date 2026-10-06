/**
 * E5 — Mood and sleep check-in.
 *
 * Four Rating components (mood, stress, sleep quality, energy), each 1–5.
 * Saves via useFinishLog → E6.
 */
import { useState } from 'react'
import { useFinishLog } from './useFinishLog'
import { Header, Footer, Screen } from '@/ui/layout'
import { Rating } from '@/ui/controls'
import { Alert, Button } from '@/ui/primitives'

export function LogCheckin() {
  const [mood, setMood] = useState(3)
  const [stress, setStress] = useState(4)
  const [sleep, setSleep] = useState(2)
  const [energy, setEnergy] = useState(3)
  const { save, pending, error } = useFinishLog()
  return (
    <Screen>
      <Header title="Mood and sleep" back backTo="E1" sub="Thirty seconds. Tap a number for each." />
      <Rating label="Mood" value={mood} onChange={setMood} lowLabel="Very low" highLabel="Very good" />
      <Rating label="Stress" value={stress} onChange={setStress} lowLabel="Calm" highLabel="Very stressed" />
      <Rating label="Sleep quality" value={sleep} onChange={setSleep} lowLabel="Very poor" highLabel="Excellent" />
      <Rating label="Energy" value={energy} onChange={setEnergy} lowLabel="Exhausted" highLabel="Energised" />
      {error && <Alert tone="danger">{error}</Alert>}
      <Footer>
        <Button disabled={pending} onClick={() => save({ kind: 'checkin', mood, stress, sleep, energy })}>
          Save check-in
        </Button>
      </Footer>
    </Screen>
  )
}
