import { useState } from 'react'
import type { Intensity, WorkoutType } from '@/data/types'
import { useGo } from '@/app/navigation'
import { Header, Footer, Screen } from '@/ui/layout'
import { ChoiceCards } from '@/ui/controls'
import { Alert, Button, Card, Chip, Field, SectionTitle, Stepper, TextLink } from '@/ui/primitives'
import { Barbell, Heartbeat, Leaf, PersonSimpleWalk, Watch, Lightning } from '@/ui/icons'
import { useFinishLog } from './LogScreens'
import { Info } from '@/ui/icons'

const types: { value: WorkoutType; title: string; sub: string; icon: React.ReactNode }[] = [
  { value: 'aerobic', title: 'Aerobic', sub: 'Steady effort that raises your breathing: walking, cycling, swimming', icon: <PersonSimpleWalk size={22} aria-hidden /> },
  { value: 'strength', title: 'Strength', sub: 'Short hard effort against resistance: weights, bands, bodyweight', icon: <Barbell size={22} aria-hidden /> },
  { value: 'mixed', title: 'Mixed', sub: 'Circuit or interval training', icon: <Lightning size={22} aria-hidden /> },
  { value: 'flexibility', title: 'Flexibility and balance', sub: 'Yoga, tai chi, stretching', icon: <Leaf size={22} aria-hidden /> },
]
const activities: Record<WorkoutType, string[]> = {
  aerobic: ['Brisk walk', 'Jog', 'Cycling', 'Swimming', 'Dancing', 'Hiking', 'Badminton'],
  strength: ['Weights', 'Resistance bands', 'Bodyweight', 'Circuit'],
  mixed: ['HIIT', 'Sports'],
  flexibility: ['Yoga', 'Tai chi', 'Stretching'],
}
const intensities: { value: Intensity; title: string; sub: string }[] = [
  { value: 'light', title: 'Light', sub: 'I can talk or sing easily' },
  { value: 'moderate', title: 'Moderate', sub: 'I can talk but not sing' },
  { value: 'vigorous', title: 'Vigorous', sub: 'I can only say a few words' },
]
const feels = ['Energised', 'Fine', 'Tired', 'Unwell']

export function LogWorkout() {
  const go = useGo()
  const { save, pending } = useFinishLog()
  const [watch, setWatch] = useState<'open' | 'accepted' | 'hidden'>('open')
  const [type, setType] = useState<WorkoutType | null>(null)
  const [activity, setActivity] = useState<string | null>(null)
  const [other, setOther] = useState('')
  const [intensity, setIntensity] = useState<Intensity | null>(null)
  const [effort, setEffort] = useState(5)
  const [minutes, setMinutes] = useState(30)
  const [start, setStart] = useState('7:35 pm')
  const [feel, setFeel] = useState<string | null>(null)

  const accept = () => {
    setWatch('accepted')
    setType('aerobic')
    setActivity('Brisk walk')
    setIntensity('moderate')
    setMinutes(32)
    setStart('7:35 pm')
  }
  const name = activity === 'Other' ? other || 'Workout' : activity
  const ready = !!type && !!name && !!intensity

  return (
    <Screen>
      <Header title="Log a workout" back backTo="E1" sub="So your doctor can see how you really move." />

      {watch !== 'hidden' && (
        <Card tone="soft" className="flex flex-col gap-3">
          <div className="flex items-center gap-2 text-sub font-bold text-brand">
            <Watch size={22} aria-hidden />
            From your watch
          </div>
          <p className="text-body">Brisk walk, 32 min, average heart rate 108, 7:35 pm. Add it?</p>
          {watch === 'accepted' ? (
            <p className="flex items-center gap-2 text-sub font-bold text-ok">Added to the form below. Check it, then save.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              <Button size="md" className="!w-auto flex-1" onClick={accept}>
                Confirm
              </Button>
              <Button size="md" variant="secondary" className="!w-auto flex-1" onClick={accept}>
                Edit
              </Button>
              <Button size="md" variant="ghost" className="!w-auto" onClick={() => setWatch('hidden')}>
                Not a workout
              </Button>
            </div>
          )}
        </Card>
      )}

      <section className="flex flex-col gap-3">
        <SectionTitle>What kind?</SectionTitle>
        <ChoiceCards label="Workout type" options={types} value={type} onChange={(v) => { setType(v); setActivity(null) }} />
      </section>

      {type && (
        <section className="flex flex-col gap-3">
          <SectionTitle>Which activity?</SectionTitle>
          <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Activity">
            {[...activities[type], 'Other'].map((a) => (
              <Chip key={a} on={activity === a} onClick={() => setActivity(a)}>
                {a}
              </Chip>
            ))}
          </div>
          {activity === 'Other' && <Field label="Name it" value={other} onChange={setOther} />}
        </section>
      )}

      <section className="flex flex-col gap-3">
        <SectionTitle>How hard was it?</SectionTitle>
        <ChoiceCards label="Intensity" options={intensities} value={intensity} onChange={setIntensity} />
        {watch === 'accepted' && intensity !== 'moderate' && (
          <Alert tone="info" icon={Heartbeat}>
            Your watch suggests moderate.{' '}
            <TextLink onClick={() => setIntensity('moderate')} className="!min-h-0">
              Use it
            </TextLink>
          </Alert>
        )}
        <div className="flex flex-col gap-1">
          <label htmlFor="effort" className="text-sub font-bold">
            How hard did it feel? <span className="num text-body">{effort}</span> of 10
          </label>
          <input id="effort" type="range" min={1} max={10} value={effort} onChange={(e) => setEffort(Number(e.target.value))} className="h-12 w-full accent-[var(--c-brand)]" />
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <SectionTitle>When and how long?</SectionTitle>
        <Stepper label="minutes" value={minutes} onChange={setMinutes} min={5} max={240} step={5} format={(v) => `${v} min`} />
        <Field label="Start time" value={start} onChange={setStart} />
      </section>

      <Card className="flex flex-col gap-2">
        <p className="flex items-center gap-2 text-sub font-bold text-ink2">
          <Info size={18} aria-hidden /> Filled in for you
        </p>
        <ul className="flex flex-wrap gap-2">
          <li className="rounded-chip bg-well px-3 py-1.5 text-sub">Last meal 6 h 30 min ago</li>
          <li className="rounded-chip bg-well px-3 py-1.5 text-sub">Glucose before: 7.8 mmol/L (from your sensor)</li>
        </ul>
        <p className="text-sub text-ink2">We'll remind you to log a reading 30 minutes after, so your doctor can see how exercise affects you.</p>
      </Card>

      <section className="flex flex-col gap-3">
        <SectionTitle>How did you feel?</SectionTitle>
        <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="How you felt">
          {feels.map((f) => (
            <Chip key={f} on={feel === f} onClick={() => setFeel(f)}>
              {f}
            </Chip>
          ))}
        </div>
        {feel === 'Unwell' && <TextLink onClick={() => go('E4')} className="self-start">Log a symptom</TextLink>}
      </section>

      <Footer>
        <Button disabled={!ready || pending} onClick={() => save({ kind: 'workout', type: type!, activity: name!, intensity: intensity!, minutes, start, feel: feel ?? 'Fine' })}>
          Save workout
        </Button>
      </Footer>
    </Screen>
  )
}
