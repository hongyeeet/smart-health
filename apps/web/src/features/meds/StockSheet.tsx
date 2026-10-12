import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useStock, useStockChange } from '@/data/hooks'
import { useUi } from '@/state/store'
import { Sheet } from '@/ui/Sheet'
import { Alert, Button, Field } from '@/ui/primitives'
import { countText, unitFor } from './MedStockCard'

/** Largest number of tablets (or doses) the warehouse holds. The server enforces the same limit. */
const MAX = 10000

/**
 * The pop-up behind "I bought more" (mode 'add': the number is added to the count) and "Edit" (mode 'set': the exact count) on a medicine
 * card in "All medications" (H1). Opened with the medicine's id; the count is read from the shared stock list. A medicine with no count
 * yet has nothing to add to, so either way the pop-up asks how many the person has now and saves that as the starting count.
 * Saving writes to the database, and the cards behind it refresh when it closes.
 */
export function StockSheet({ onClose, medId, mode = 'set' }: { onClose: () => void; medId?: string; mode?: 'add' | 'set' }) {
  const { t } = useTranslation()
  const { data } = useStock()
  const med = data?.items.find((m) => m.id === medId)
  const save = useStockChange()
  const toast = useUi((s) => s.showToast)
  const hasCount = med?.stockCount != null
  const isAdd = mode === 'add' && hasCount
  const unit = med?.stockUnit || t('stock.units', 'doses')
  const [value, setValue] = useState(() => (!isAdd && med?.stockCount != null ? countText(med.stockCount) : ''))

  const parsed = value.trim() === '' ? null : Number(value.trim().replace(',', '.'))
  const problem =
    parsed === null ? null
    : !Number.isFinite(parsed) ? t('stock.badNumber', 'Please enter a number.')
    : parsed < 0 || parsed > MAX ? t('stock.range', 'Please enter a number from 0 to 10000.')
    : isAdd && parsed === 0 ? t('stock.addPositive', 'Enter how many you bought.')
    : null
  const canSave = med !== undefined && parsed !== null && problem === null && !save.isPending
  const after = isAdd && parsed !== null && problem === null && med?.stockCount != null ? med.stockCount + parsed : null

  const title = !hasCount ? t('stock.startTitle', 'How many do you have?') : isAdd ? t('stock.buyTitle', 'I bought more') : t('stock.editTitle', 'Edit the number')

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
    <Sheet title={title} onClose={onClose} label={med ? `${title}: ${med.name}` : undefined}>
      {!med ? (
        <p className="text-body text-ink2">{t('stock.gone', 'This medicine is no longer in your list.')}</p>
      ) : (
        <div className="flex flex-col gap-4">
          <p className="text-body font-bold">
            {med.name}
            {med.strength && med.strength !== 'Strength not entered' && !med.name.includes(med.strength) && <span className="font-normal text-ink2"> {med.strength}</span>}
          </p>

          {isAdd ? (
            <>
              <p className="text-sub text-ink2">{t('stock.buyLine', 'How many {{unit}} did you buy? The number is added to what you have now.', { unit })}</p>
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
              {hasCount
                ? t('stock.setLine', 'Type the exact number you have now. You can change it at any time.')
                : t('stock.startLine', 'How many {{unit}} do you have now? The number then goes down by itself each time you mark a dose as taken.', { unit })}
            </p>
          )}

          <Field
            label={isAdd ? t('stock.howManyAdd', 'How many to add') : t('stock.howManyNow', 'How many are left now')}
            value={value}
            onChange={setValue}
            inputMode="decimal"
            placeholder="0"
            hint={
              isAdd && med.stockCount != null
                ? after !== null
                  ? t('stock.afterBuy', 'You have {{now}} {{unit}} now. After this: {{after}}.', { now: countText(med.stockCount), unit: unitFor(med.stockUnit, med.stockCount), after: countText(after) })
                  : t('stock.haveNow', 'You have {{now}} {{unit}} now.', { now: countText(med.stockCount), unit: unitFor(med.stockUnit, med.stockCount) })
                : undefined
            }
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
