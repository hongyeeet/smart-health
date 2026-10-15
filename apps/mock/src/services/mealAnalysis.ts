/**
 * Meal analysis (F6). The real service sends the photo or text to the vision model and returns items with
 * estimated nutrients and a confidence per field. Everything it returns is an estimate until the user confirms it.
 * This mock answers from a small keyword table so the screens behave like the real thing.
 */
export interface Macros {
  kcal: number
  carbsG: number
  proteinG: number
  fatG: number
  fibreG: number
  sugarG: number
  saltMg: number
}

export interface MealAnalysis {
  name: string
  items: string[]
  macros: Macros
  confidence: 'high' | 'check'
  flags: ('high_salt' | 'high_sugar')[]
}

export interface MealAnalysisService {
  fromText(text: string): Promise<MealAnalysis>
  fromPhoto(): Promise<MealAnalysis>
}

const table: { re: RegExp; name: string; items: string[]; m: Macros; salty?: boolean; sweet?: boolean }[] = [
  { re: /chicken rice/, name: 'Chicken rice', items: ['White rice', 'Poached chicken', 'Cucumber'], m: { kcal: 620, carbsG: 82, proteinG: 30, fatG: 20, fibreG: 2, sugarG: 3, saltMg: 1500 }, salty: true },
  { re: /laksa/, name: 'Laksa', items: ['Rice noodles', 'Coconut curry gravy', 'Prawns', 'Beansprouts'], m: { kcal: 590, carbsG: 74, proteinG: 22, fatG: 24, fibreG: 4, sugarG: 6, saltMg: 2300 }, salty: true },
  { re: /kaya|toast/, name: 'Kaya toast with soft eggs', items: ['Toast', 'Kaya', 'Soft-boiled eggs'], m: { kcal: 380, carbsG: 36, proteinG: 14, fatG: 18, fibreG: 2, sugarG: 14, saltMg: 520 }, sweet: true },
  { re: /egg|vegetable|omelette/, name: 'Vegetable and egg breakfast', items: ['Eggs', 'Mixed vegetables'], m: { kcal: 260, carbsG: 22, proteinG: 16, fatG: 12, fibreG: 5, sugarG: 4, saltMg: 400 } },
  { re: /mee goreng|noodle/, name: 'Mee goreng', items: ['Fried noodles', 'Egg', 'Vegetables'], m: { kcal: 640, carbsG: 88, proteinG: 18, fatG: 24, fibreG: 4, sugarG: 7, saltMg: 1900 }, salty: true },
  { re: /rice/, name: 'Rice with chicken and vegetables', items: ['White rice', 'Chicken', 'Vegetables'], m: { kcal: 560, carbsG: 78, proteinG: 28, fatG: 14, fibreG: 4, sugarG: 4, saltMg: 1250 }, salty: true },
]

const fallback: MealAnalysis = { name: 'Your meal', items: ['Mixed meal'], macros: { kcal: 450, carbsG: 50, proteinG: 20, fatG: 16, fibreG: 4, sugarG: 6, saltMg: 800 }, confidence: 'check', flags: [] }
const wait = (ms: number) => new Promise((r) => setTimeout(r, ms))

export const mealAnalysisService: MealAnalysisService = {
  async fromText(text) {
    await wait(500)
    const t = text.toLowerCase()
    const hit = table.find((x) => x.re.test(t))
    if (!hit) return { ...fallback, name: text.trim() ? text.trim().replace(/^./, (c) => c.toUpperCase()) : fallback.name }
    return { name: hit.name, items: hit.items, macros: hit.m, confidence: 'high', flags: [...(hit.salty ? (['high_salt'] as const) : []), ...(hit.sweet ? (['high_sugar'] as const) : [])] }
  },
  async fromPhoto() {
    await wait(1100)
    const hit = table[0]!
    return { name: hit.name, items: hit.items, macros: hit.m, confidence: 'check', flags: ['high_salt'] }
  },
}
