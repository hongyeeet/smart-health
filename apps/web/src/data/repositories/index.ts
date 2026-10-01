import type { Api } from './types'
import { httpApi } from './http'

/** The production data layer. The clickable mock lives in apps/mock and uses an in-memory implementation of the same interface. */
export const api: Api = httpApi
export type { Api, LogInput, NewMedication } from './types'
