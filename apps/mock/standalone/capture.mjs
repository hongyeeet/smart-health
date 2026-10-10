/**
 * Records real API answers into apps/mock/standalone/snapshot.json, for the single-file copy of the app (build.mjs).
 *
 * Needs the API running on :8000 (set API=http://host:port to change it). Reads for both users are recorded as they are. For the writes
 * (logging a meal, a workout, a symptom, a check-in, and a photo analysis) it makes one real call each and deletes the entry again, so the
 * copy can show what a saved log and an analysis look like. Run it with:  node apps/mock/standalone/capture.mjs
 */
import { readFile, writeFile, mkdir } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const API = (process.env.API ?? 'http://localhost:8000') + '/api/v1'
const here = dirname(fileURLToPath(import.meta.url))
const out = resolve(here, 'snapshot.json')
const photo = resolve(here, '..', '..', '..', 'data', 'raw', 'demo', 'chicken_rice.jpg')

const get = async (user, path) => {
  const res = await fetch(API + path, { headers: { 'X-User': user } })
  if (!res.ok) return null
  return res.json()
}

const common = [
  '/users', '/notifications', '/logs/today', '/logs/recent', '/logs/context', '/nutrition/flags', '/nutrition/lunch',
  '/memory/facts', '/memory/digest', '/memory/audit', '/memory/progress', '/memory/usage', '/workouts/week', '/medications', '/doses/today', '/interactions',
  ...[7, 14, 30, 90].map((d) => `/brief/report?days=${d}`),
  ...['overview', 'glucose', 'food', 'activity', 'sleep', 'medication'].flatMap((t) => [7, 30, 90].map((d) => `/insights/${t}?days=${d}`)),
  '/insights/sprint',
]

const reads = {}
for (const user of ['demo', 'mr-tan']) {
  for (const path of common) {
    const body = await get(user, path)
    if (body !== null) reads[`${user}|${path}`] = body
  }
  const meds = reads[`${user}|/medications`]
  for (const m of (Array.isArray(meds) ? meds : (meds?.medications ?? []))) {
    const detail = await get(user, `/medications/${m.id}`)
    if (detail) reads[`${user}|/medications/${m.id}`] = detail
  }
  console.log(user, 'reads so far:', Object.keys(reads).filter((k) => k.startsWith(user + '|')).length)
}

// One real write of each kind, for the shape of the answer. Each entry is deleted straight away.
const now = new Date()
const iso = (m) => new Date(now.getTime() - m * 60000).toISOString()
const bodies = {
  meal: { kind: 'meal', name: 'Sample meal', startAt: iso(30), endAt: iso(0), portion: 1, kcal: 600, carbsG: 70, proteinG: 25, fatG: 20, sodiumMg: 900 },
  workout: { kind: 'workout', type: 'walking', activity: 'Sample walk', intensity: 3, startAt: iso(30), minutes: 30, feeling: 4 },
  symptom: { kind: 'symptom', label: 'Headache', severity: 2, occurredAt: iso(0), durationMin: 20 },
  checkin: { kind: 'checkin', mood: 4, stress: 2, sleep: 4, energy: 4 },
}
const writes = { logs: {} }
for (const [kind, body] of Object.entries(bodies)) {
  const res = await fetch(API + '/logs', { method: 'POST', headers: { 'X-User': 'demo', 'Content-Type': 'application/json' }, body: JSON.stringify(body) })
  const json = await res.json()
  writes.logs[kind] = json
  if (json?.id) await fetch(API + `/logs/${json.id}`, { method: 'DELETE', headers: { 'X-User': 'demo' } })
}
const fd = new FormData()
fd.append('file', new Blob([await readFile(photo)], { type: 'image/jpeg' }), 'meal.jpg')
const an = await fetch(API + '/meals/analyze', { method: 'POST', headers: { 'X-User': 'demo' }, body: fd })
writes.analysis = an.ok ? await an.json() : null

await mkdir(dirname(out), { recursive: true })
await writeFile(out, JSON.stringify({ takenAt: now.toISOString(), reads, writes }))
console.log('wrote', out, Object.keys(reads).length, 'reads;', 'analysis:', !!writes.analysis)
