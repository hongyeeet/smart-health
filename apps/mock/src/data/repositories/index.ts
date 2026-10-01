import type { Api } from './types'
import { mockApi } from './mock'

/**
 * Swap this line for the real client when the backend exists:
 *   export const api: Api = httpApi
 */
export const api: Api = mockApi
export type { Api, LogInput, NewMedication } from './types'
