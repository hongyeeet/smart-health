/**
 * The single-file copy of the app has no server. This replaces `fetch` for the app's own calls (/api/v1/...) with answers recorded from
 * the real API (snapshot.json, made by capture.mjs), so every screen shows real data for both people.
 *
 *  - Reads come from the snapshot, for whoever the X-User header names. Anything not recorded answers 404 and the screen shows its
 *    normal "could not load" state.
 *  - Writes (logging, taking a dose, a photo) answer success and are kept in memory only, so the flow can be walked through. The
 *    list of recent entries reflects what was logged in this session. Nothing is saved when the page closes.
 *  - Medicine scanning needs a camera, a reader and a model, so it answers with an explanation instead of a result.
 */
import snapshot from './snapshot.json'

type Json = unknown
interface Snapshot {
  takenAt: string
  reads: Record<string, Json>
  writes: { logs: Record<string, Record<string, unknown>>; analysis: Json }
}
const snap = snapshot as unknown as Snapshot
const BASE = '/api/v1'

const userOf = (init?: RequestInit): string => {
  const h = init?.headers
  if (!h) return 'demo'
  if (h instanceof Headers) return h.get('X-User') ?? 'demo'
  if (Array.isArray(h)) return h.find(([k]) => k.toLowerCase() === 'x-user')?.[1] ?? 'demo'
  const rec = h as Record<string, string>
  return rec['X-User'] ?? rec['x-user'] ?? 'demo'
}

const reply = (body: Json, status = 200) =>
  new Response(status === 204 ? null : JSON.stringify(body ?? {}), { status, headers: { 'Content-Type': 'application/json' } })

/** What was logged in this session, newest first, per person. */
const added: Record<string, Record<string, unknown>[]> = {}
const removed = new Set<string>()
let counter = 0

const clock = (d: Date) => d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }).toLowerCase()

function logWrite(user: string, input: Record<string, unknown>) {
  const kind = String(input.kind)
  const template = snap.writes.logs[kind] ?? snap.writes.logs.meal!
  const id = `offline-${++counter}`
  const when = new Date()
  const title =
    kind === 'meal' ? String(input.name ?? 'Meal') : kind === 'workout' ? String(input.activity || 'Workout') : kind === 'symptom' ? String(input.label ?? 'Symptom') : 'Check-in'
  const result = { ...template, id, title: kind === 'meal' ? 'Meal saved' : template.title, day: 'Today' }
  ;(added[user] ??= []).unshift({
    id, kind, title, detail: String(template.detail ?? ''), when: clock(when), date: when.toISOString().slice(0, 10),
  })
  return result
}

async function handle(user: string, method: string, path: string, init?: RequestInit): Promise<Response> {
  const [route, query = ''] = path.split('?')
  const key = `${user}|${route}${query ? `?${query}` : ''}`

  if (method === 'GET') {
    if (route === '/logs/recent') {
      const base = (snap.reads[key] as Record<string, unknown>[] | undefined) ?? []
      return reply([...(added[user] ?? []), ...base].filter((e) => !removed.has(String(e.id))))
    }
    if (route === '/meals/response') return reply({ kind: 'learning', text: 'Still learning how you respond to this meal. We need at least 2 times.', n: 0, range: null })
    if (key in snap.reads) return reply(snap.reads[key])
    return reply({ detail: 'This was not recorded in the offline copy.' }, 404)
  }

  if (route === '/meals/analyze') return reply(snap.writes.analysis ?? { detail: 'Photo analysis is not available in the offline copy.' }, snap.writes.analysis ? 200 : 503)
  if (route === '/logs' && method === 'POST') return reply(logWrite(user, JSON.parse(String(init?.body ?? '{}'))))
  if (method === 'DELETE' && route.startsWith('/logs/')) {
    removed.add(route.slice('/logs/'.length))
    return reply(null, 204)
  }
  if (route === '/scans') return reply({ detail: 'Scanning a medicine label needs a camera and the live service. It is not available in the offline copy. Use "Add by hand" instead.' }, 503)
  if (route.endsWith('/explanation')) {
    const id = route.split('/')[2]
    const detail = snap.reads[`${user}|/medications/${id}`] as { explanation?: unknown } | undefined
    return detail?.explanation ? reply(detail.explanation) : reply({ detail: 'No explanation was recorded for this medicine.' }, 404)
  }
  if (method === 'DELETE') return reply(null, 204)
  return reply({})
}

export function installShim() {
  const real = window.fetch.bind(window)
  window.fetch = (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url
    const at = url.indexOf(BASE)
    if (at === -1) return real(input, init)
    const method = (init?.method ?? (typeof input === 'object' && 'method' in input ? input.method : 'GET')).toUpperCase()
    return handle(userOf(init), method, url.slice(at + BASE.length), init)
  }
  ;(window as unknown as { __offlineSnapshot: string }).__offlineSnapshot = snap.takenAt
}
