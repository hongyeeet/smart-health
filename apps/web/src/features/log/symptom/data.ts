/**
 * The symptom choices for Log a symptom (E4). `value` is the English name that is saved and checked, so it never
 * changes; `key` and `text` are only the words shown on screen.
 */
export interface Choice {
  value: string
  key: string
  text: string
}

const c = (value: string, key: string, text: string = value): Choice => ({ value, key, text })

export const SYMPTOM_GROUPS: { key: string; name: string; items: Choice[] }[] = [
  {
    key: 'log.sym.gThirst',
    name: 'Thirst and urine',
    items: [c('More thirsty than usual', 'log.sym.thirsty'), c('Passing more urine', 'log.sym.urine')],
  },
  {
    key: 'log.sym.gNerves',
    name: 'Nerves and feet',
    items: [c('Numbness', 'log.sym.numbness'), c('Tingling', 'log.sym.tingling'), c('Foot pain', 'log.sym.footPain')],
  },
  { key: 'log.sym.gEyes', name: 'Eyes', items: [c('Blurry vision', 'log.sym.blurry')] },
  {
    key: 'log.sym.gEnergy',
    name: 'Energy and head',
    items: [c('Tired more than usual', 'log.sym.tired'), c('Dizzy', 'log.sym.dizzy'), c('Headache', 'log.sym.headache')],
  },
  { key: 'log.sym.gStomach', name: 'Stomach', items: [c('Upset stomach', 'log.sym.stomach'), c('Vomiting', 'log.sym.vomiting')] },
  {
    key: 'log.sym.gSkin',
    name: 'Skin and other',
    items: [c('Night sweats', 'log.sym.nightSweats'), c('Slow-healing wound', 'log.sym.wound'), c('Something else', 'log.sym.other')],
  },
]

/** Red-flag symptoms: saving one goes straight to urgent help. The saved value is the full English name. */
export const RED_FLAGS: Choice[] = [
  c('Chest pain', 'log.sym.chestPain'),
  c('Confusion', 'log.sym.confusion'),
  c('Fainting', 'log.sym.fainting'),
  c('Breathlessness at rest', 'log.sym.breathless'),
  c('Sudden vision loss or a curtain across my vision', 'log.sym.visionLossShort', 'Sudden vision loss'),
]
export const RED_VALUES = RED_FLAGS.map((r) => r.value)

export const SIDE_SYMPTOMS = ['Numbness', 'Tingling', 'Foot pain']
export const SIDES: Choice[] = [
  c('Left foot', 'log.sym.leftFoot'),
  c('Right foot', 'log.sym.rightFoot'),
  c('Both feet', 'log.sym.bothFeet'),
  c('Hands', 'log.sym.hands'),
  c('Somewhere else', 'log.sym.elsewhere'),
]
export const RELATIONS: Choice[] = [
  c('Before a meal', 'log.sym.beforeMeal'),
  c('After a meal', 'log.sym.afterMeal'),
  c('After exercise', 'log.sym.afterExercise'),
  c('At rest', 'log.sym.atRest'),
  c('While asleep', 'log.sym.asleep'),
]
export const DIZZY_FEELS: Choice[] = [c('When I stand up', 'log.sym.standUp'), c('Shaky or sweaty', 'log.sym.shaky'), c('Spinning', 'log.sym.spinning')]

/** Minutes the symptom lasted; 'unknown' is "still going or not sure". */
export const DURATIONS: (number | 'unknown')[] = [5, 10, 15, 30, 60, 120, 'unknown']

/** Strength 1 to 5: the word, and the tile colours (soft when not picked, solid when picked). */
export const STRENGTH: { n: number; key: string; word: string; soft: string; text: string; solid: string }[] = [
  { n: 1, key: 'log.sym.s1', word: 'Mild', soft: 'bg-ok-soft text-ok', text: 'text-ok', solid: 'bg-ok text-card' },
  { n: 2, key: 'log.sym.s2', word: 'Noticeable', soft: 'bg-brass-soft text-brass', text: 'text-brass', solid: 'bg-brass text-card' },
  { n: 3, key: 'log.sym.s3', word: 'Moderate', soft: 'bg-brass-soft text-brass', text: 'text-brass', solid: 'bg-brass text-card' },
  { n: 4, key: 'log.sym.s4', word: 'Strong', soft: 'bg-warn-soft text-warn', text: 'text-warn', solid: 'bg-warn text-card' },
  { n: 5, key: 'log.sym.s5', word: 'Severe', soft: 'bg-danger-soft text-danger', text: 'text-danger', solid: 'bg-danger text-card' },
]

/** Every choice on the page, for looking up the words to show for a saved value. */
export const CHOICES: Choice[] = [...SYMPTOM_GROUPS.flatMap((g) => g.items), ...RED_FLAGS, ...SIDES, ...RELATIONS, ...DIZZY_FEELS]
