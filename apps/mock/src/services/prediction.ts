import { foodResponses } from '@/data/fixtures/mrTan'

/**
 * Personal food-response note (F7). Today it reads the demo sensor sprint; later it can call the
 * baseline model (task E1-5) behind the same interface. It describes what was measured for this
 * person. It never predicts a diagnosis or gives advice, and it needs at least 2 observations.
 */
export interface FoodNote {
  kind: 'higher' | 'lower' | 'similar' | 'learning'
  text: string
  n: number
  range?: [number, number]
}

export interface PredictionService {
  foodNote(foodName: string): Promise<FoodNote | null>
}

const words = (s: string) => s.toLowerCase().split(/[^a-z]+/).filter((w) => w.length > 2)

export const predictionService: PredictionService = {
  async foodNote(name) {
    const q = new Set(words(name))
    if (!q.size) return null
    const hit = foodResponses
      .map((f) => ({ f, score: words(f.name).filter((w) => q.has(w)).length }))
      .filter((x) => x.score > 0)
      .sort((a, b) => b.score - a.score)[0]?.f
    if (!hit) return { kind: 'learning', text: 'Still learning how you respond to this meal.', n: 0 }
    if (hit.n < 2) return { kind: 'learning', text: 'Still learning how you respond to this meal. We need at least 2 times.', n: hit.n }
    const sorted = [...foodResponses].filter((f) => f.n >= 2).sort((a, b) => a.rise - b.rise)
    const rank = sorted.findIndex((f) => f.id === hit.id) / (sorted.length - 1)
    if (rank >= 0.66) return { kind: 'higher', text: 'Last time you had this, your glucose rose more than after most of your meals.', n: hit.n, range: [hit.min, hit.max] }
    if (rank <= 0.33) return { kind: 'lower', text: 'Last time you had this, your glucose rose less than after most of your meals.', n: hit.n, range: [hit.min, hit.max] }
    return { kind: 'similar', text: 'Your glucose rose about as much as after most of your meals.', n: hit.n, range: [hit.min, hit.max] }
  },
}
