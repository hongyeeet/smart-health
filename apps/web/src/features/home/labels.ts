import type { TFunction } from 'i18next'

/** The name of a "today's logging" item (meals, check-in, workout, symptoms, blood pressure) in the person's language. The server sends the key and an English label. */
export const progressLabel = (t: TFunction, key: string, fallback: string): string => t(`home.itemLabel.${key}`, { defaultValue: fallback })
