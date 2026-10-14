import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Footer } from '@/ui/layout'
import { Button, Card, Field, TextLink } from '@/ui/primitives'
import { Camera, ForkKnife } from '@/ui/icons'

interface Props {
  /** object URL of the chosen photo, or null before one is chosen */
  preview: string | null
  /** phones and tablets open the camera; laptops only offer a file to upload */
  isTouch: boolean
  description: string
  onDescription: (v: string) => void
  onOpenCamera: () => void
  onOpenGallery: () => void
  onRead: () => void
  onManual: () => void
}

/**
 * Step 1: the photo (a big dashed target with the two ways to get one), the three tips and the optional note. One column on a
 * phone; the tips sit beside the photo from a laptop up.
 */
export function MealPhotoStep({ preview, isTouch, description, onDescription, onOpenCamera, onOpenGallery, onRead, onManual }: Props) {
  const { t } = useTranslation()
  const tips = [
    t('log.meal.tip1', 'Take one photo of the whole plate or bowl.'),
    t('log.meal.tip2', 'Use good light, with the food in the middle.'),
    t('log.meal.tip3', 'Say below what the photo can not show.'),
  ]
  return (
    <>
      <Card className="flex flex-col gap-5 lg:flex-row lg:items-stretch">
        <div className="min-w-0 flex-1">
          {preview ? (
            <PhotoPreview key={preview} src={preview} onChange={isTouch ? onOpenCamera : onOpenGallery} />
          ) : (
            <div className="flex min-h-64 flex-col items-center justify-center gap-3 rounded-card border-2 border-dashed border-line bg-well p-6 text-center lg:h-full">
              <span className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-soft text-brand">
                <Camera size={32} aria-hidden />
              </span>
              <p className="text-h2 font-bold text-ink">{t('log.meal.addPhoto', 'Add a photo of your meal')}</p>
              <div className="mt-1 flex flex-wrap justify-center gap-3">
                {isTouch ? (
                  <>
                    <div className="w-full min-w-44 sm:w-auto">
                      <Button onClick={onOpenCamera}>{t('log.meal.takePhoto', 'Take a photo')}</Button>
                    </div>
                    <div className="w-full min-w-44 sm:w-auto">
                      <Button variant="secondary" onClick={onOpenGallery}>
                        {t('log.meal.chooseFiles', 'Choose from files')}
                      </Button>
                    </div>
                  </>
                ) : (
                  <div className="w-full min-w-44 sm:w-auto">
                    <Button onClick={onOpenGallery}>{t('log.meal.chooseFiles', 'Choose from files')}</Button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-3 lg:w-[300px] lg:flex-none">
          <p className="text-body font-bold text-ink">{t('log.meal.tipsTitle', 'For a good reading')}</p>
          <ol className="flex flex-col gap-3">
            {tips.map((tip, i) => (
              <li key={i} className="flex items-start gap-3 text-sub text-ink">
                <span className="flex h-7 w-7 flex-none items-center justify-center rounded-full bg-brand-soft text-micro font-bold text-brand">{i + 1}</span>
                <span className="min-w-0 break-words">{tip}</span>
              </li>
            ))}
          </ol>
          <div className="mt-auto pt-2">
            <Field
              label={t('log.meal.anything', "Anything the photo can't show? (optional)")}
              value={description}
              onChange={onDescription}
              multiline
              placeholder={t('log.meal.anythingPh', 'Optional: only ate half the rice, no gravy, teh kosong')}
            />
          </div>
        </div>
      </Card>
      <Footer>
        <TextLink onClick={onManual} icon={ForkKnife} className="self-center md:self-center">
          {t('log.meal.byHandInstead', 'Enter the meal by hand instead')}
        </TextLink>
        <Button icon={ForkKnife} disabled={!preview} onClick={onRead}>
          {t('log.meal.analyse', 'Read my meal')}
        </Button>
      </Footer>
    </>
  )
}

/** The chosen photo with a "Change photo" button. Some browsers cannot show a photo they can still send, so a failed preview is said plainly. */
export function PhotoPreview({ src, onChange, changeLabel, compact = false }: { src: string; onChange: () => void; changeLabel?: string; compact?: boolean }) {
  const { t } = useTranslation()
  const [failed, setFailed] = useState(false)
  return (
    <div
      className={
        compact
          ? 'relative h-44 overflow-hidden rounded-card border border-line bg-well sm:h-[156px]'
          : 'relative overflow-hidden rounded-card border border-line bg-well'
      }
    >
      {failed ? (
        <p className="flex h-full min-h-56 items-center justify-center p-6 text-center text-sub text-ink2">
          {t('log.meal.noPreview', 'This photo cannot be shown here, but it can still be read.')}
        </p>
      ) : (
        <img
          src={src}
          alt={t('log.meal.alt', 'Your meal')}
          className={compact ? 'h-full w-full object-cover' : 'max-h-80 w-full object-cover'}
          onError={() => setFailed(true)}
        />
      )}
      <button type="button" onClick={onChange} className="press absolute right-3 top-3 min-h-12 rounded-chip bg-ink/80 px-4 text-sub font-bold text-canvas">
        {changeLabel ?? t('log.meal.changePhoto', 'Change photo')}
      </button>
    </div>
  )
}
