/**
 * The name a person reads for a device code (for example "dexcom" or "fitbit") on K4 and in the doctor report. The same names as the
 * onboarding choices and the server's device_display_name (services/api/app/services/onboarding.py). Unknown codes are title-cased.
 */
const DEVICE_NAMES: Record<string, string> = {
  libre: 'Abbott FreeStyle Libre',
  dexcom: 'Dexcom',
  apple: 'Apple Watch',
  garmin: 'Garmin',
  samsung: 'Samsung Galaxy Watch',
  fitbit: 'Fitbit',
  xiaomi: 'Xiaomi',
  other: 'Other',
  none: 'None',
}

export function deviceName(code: string): string {
  const known = DEVICE_NAMES[code.toLowerCase()]
  return known ?? code.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}
