import i18n from '@/i18n'

/**
 * The locale to format dates, weekdays, months and clock times in. English keeps whichever English format the screen already used
 * (en-GB for "13 Oct", en-SG, en-US for "7:00 am"); Chinese, Malay and Tamil use their own Singapore formats, so month and weekday names
 * are in the person's language. Numbers (readings, kcal, mg) are never given a language: the digits stay the same everywhere.
 * Call it when formatting, not once at the top of a file, so a change of language shows at once.
 */
const OWN: Record<string, string> = { zh: 'zh-SG', ms: 'ms-SG', ta: 'ta-SG' }

export function dateLocale(english: string): string {
  return OWN[i18n.language] ?? english
}
