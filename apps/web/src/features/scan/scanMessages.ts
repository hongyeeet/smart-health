import { useTranslation } from 'react-i18next'

/**
 * The words for a scan that could not be read, by the stable code the API returns (`errorCode`, docs/specs/f2-scan.md). Every code has
 * a plain message and a way forward: retake the photo or type it in. Unknown or missing codes use the general sentence.
 */
export function useScanFailureText(): (code: string | null | undefined) => string {
  const { t } = useTranslation()
  const general = t('scan.fail.general', 'We could not read this. Take another photo or type it in.')
  return (code) => {
    switch (code) {
      case 'model_unavailable':
      case 'ocr_unavailable':
        return t('scan.fail.readerDown', 'The label reader is not working right now. Try again in a moment, or type it in.')
      case 'daily_limit':
        return t('scan.fail.dailyLimit', 'Reading photos is paused for today. You can type the medicine in instead.')
      case 'storage_unavailable':
        return t('scan.fail.storage', 'We could not save the photo just now. Please try again, or type it in.')
      case 'not_a_medicine':
        return t('scan.fail.notMedicine', 'This does not look like a medicine label. Take another photo of the label, or type it in.')
      case 'file_empty':
      case 'file_too_large':
      case 'file_type_not_allowed':
        return t('scan.fail.file', 'That photo could not be used. Take another photo, or type it in.')
      default:
        return general
    }
  }
}

/**
 * The codes where the photo gave no usable medicine at all: the screen says so and offers Retake and Type it in. The other codes
 * (low_confidence, missing_required, several_items) are partial reads: the typed form opens with the reason (D-064).
 */
export const NOT_READ_CODES = new Set([
  'ocr_empty', 'unreadable', 'not_a_medicine', 'invalid_json', 'low_confidence_all', 'model_unavailable', 'ocr_unavailable', 'daily_limit',
  'storage_unavailable', 'file_empty', 'file_too_large', 'file_type_not_allowed',
])
