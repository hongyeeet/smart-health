import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useStock, useStockChange } from '@/data/hooks'
import { useUi } from '@/state/store'
import { Sheet } from '@/ui/Sheet'
import { Alert, Button, Field } from '@/ui/primitives'

/** Largest number of tablets (or doses) the warehouse holds. The server enforces the same limit. */
const MAX = 10000

/**
 * "I bought more" (mode 'add': the number is added to the count) and "Change the number" (mode 'set': the exact count) for one of the
 * medicines in My stock (H1). Opened from the stock card with the medicine's id; the count is read from the shared stock list.
 */
export function StockSheet({ onClose, medId, mode = 'set' }: { onClose: () => void; medId?: string; mode?: 'add' | 'set' }) {
  const { t } = useTranslation()
  const { data } = useStock()
  const med = data?.items.find((m) => m.id === medId)
  const save = useStockChange()
  const toast = useUi((s) => s.showToast)
  const isAdd = mode === 'add'
  const unit = med?.stockUnit ?? ''
  const [value, setValue] = useState(() => (!isAdd && med?.stockCount != null ? String(med.stockCount) : ''))

  const parsed = value.trim() === '' ? null : Number(value.trim().replace(',', '.'))
  const problem =
    parsed === null ? null
    : !Number.isFinite(parsed) ? t('stock.badNumber', 'Please enter a number.')
    : parsed < 0 || parsed > MAX ? t('stock.range', 'Please enter a number from 0 to 10000.')
    : isAdd && parsed === 0 ? t('stock.addPositive', 'Enter how many you bought.')
    : null
  const canSave = med !== undefined && parsed !== null && problem === null && !save.isPending

  const submit = () => {
    if (!med || parsed === null || problem) return
    save.mutate({ id: med.id, change: isAdd ? { add: parsed } : { set: parsed } }, {
      onSuccess: () => {
        toast(t('stock.saved', 'Saved'))
        onClose()
      },
    })
  }

  // A refusal from the server is in plain words; a status code alone is not shown to the person.
  const failure = save.isError && save.error instanceof Error && !/^\d{3}\s/.test(save.error.message) ? save.error.message : t('stock.saveError', 'We could not save that. Please try again.')

  return (
    <Sheet title={isAdd ? t('stock.buyTitle', 'I bought more') : t('stock.setTitle', 'Change the number')} onClose={onClose} label={med ? `${isAdd ? t('stock.buyTitle', 'I bought more') : t('stock.setTitle', 'Change the number')}: ${med.name}` : undefined}>
      {!med ? (
        <p className="text-body text-ink2">{t('stock.gone', 'This medicine is no longer in your list.')}</p>
      ) : (
        <div className="flex flex-col gap-4">
          <p className="text-body font-bold">
            {med.name}
            {med.strength && med.strength !== 'Strength not entered' && <span className="font-normal text-ink2"> {med.strength}</span>}
          </p>

          {isAdd ? (
            <>
              <p className="text-sub text-ink2">
                {t('stock.buyLine', 'How many {{unit}} did you buy? The number is added to what you have now.', { unit: unit || t('stock.units', 'doses') })}
              </p>
              {med.packSize && (
                <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                  <Button variant="secondary" size="md" onClick={() => setValue(String(med.packSize))}>
                    {t('stock.onePack', 'One pack: {{n}}', { n: med.packSize })}
                  </Button>
                  <Button variant="secondary" size="md" onClick={() => setValue(String(med.packSize! * 2))}>
                    {t('stock.twoPacks', 'Two packs: {{n}}', { n: med.packSize * 2 })}
                  </Button>
                </div>
              )}
            </>
          ) : (
            <p className="text-sub text-ink2">
              {t('stock.setLine', 'Type the exact number you have now. You can change it at any time.')}
            </p>
          )}

          <Field
            label={isAdd ? t('stock.howManyAdd', 'How many to add') : t('stock.howManyNow', 'How many are left now')}
            value={value}
            onChange={setValue}
            inputMode="decimal"
            placeholder="0"
            hint={isAdd ? t('stock.addHint', 'Your count goes up by this much.') : undefined}
            error={problem ?? undefined}
            large
          />

          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <Button onClick={submit} disabled={!canSave}>
              {save.isPending ? t('stock.saving', 'Saving…') : t('stock.save', 'Save')}
            </Button>
            <Button variant="ghost" onClick={onClose} disabled={save.isPending}>
              {t('stock.cancel', 'Cancel')}
            </Button>
          </div>
          {save.isError && <Alert tone="warn">{failure}</Alert>}
        </div>
      )}
    </Sheet>
  )
}
