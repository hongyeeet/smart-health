import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Footer, Split } from '@/ui/layout'
import { Button, Card, Field, TextLink } from '@/ui/primitives'
import { Camera, ForkKnife, Image as ImageIcon } from '@/ui/icons'

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

/** Step 1: the photo (a big target), the tips and the optional description. One column on a phone, two on a tablet and laptop. */
export function MealPhotoStep({ preview, isTouch, description, onDescription, onOpenCamera, onOpenGallery, onRead, onManual }: Props) {
  const { t } = useTranslation()
  const change = isTouch ? onOpenCamera : onOpenGallery
  return (
    <>
      <Split>
        <section className="flex flex-col gap-3">
          {preview ? (
            <PhotoPreview key={preview} src={preview} onChange={change} />
          ) : (
            <button
              type="button"
              onClick={change}
              className="press flex min-h-64 w-full flex-col items-center justify-center gap-3 rounded-card border-2 border-dashed border-line bg-well p-6 text-center"
            >
              <span className="flex h-16 w-16 items-center justify-center rounded-full bg-brand-soft text-brand">
                <Camera size={32} aria-hidden />
              </span>
              <span className="text-h2 font-bold text-ink">
                {isTouch ? t('log.meal.takePhoto', 'Take a photo of your meal') : t('log.meal.choosePhoto', 'Choose a photo of your meal')}
              </span>
              <span className="text-sub text-ink2">
                {isTouch ? t('log.meal.opensCamera', 'Opens your camera') : t('log.meal.chooseFile', 'Pick a photo from your files')}
              </span>
            </button>
          )}
          {!preview && isTouch && (
            <Button variant="secondary" icon={ImageIcon} onClick={onOpenGallery}>
              {t('log.meal.upload', 'Choose from your photos')}
            </Button>
          )}
        </section>

        <section className="flex flex-col gap-4">
          <Card tone="soft" className="flex flex-col gap-2">
            <p className="text-body font-bold text-ink">{t('log.meal.tipsTitle', 'For a good reading')}</p>
            <ul className="flex list-disc flex-col gap-1.5 ps-5 text-sub text-ink2">
              <li>{t('log.meal.tip1', 'Take one photo of the whole plate or bowl.')}</li>
              <li>{t('log.meal.tip2', 'Use good light, and keep the food in the middle of the frame.')}</li>
              <li>{t('log.meal.tip3', 'If the photo cannot show something (half the rice, no gravy), say so below.')}</li>
              <li>{t('log.meal.tip4', 'The numbers are estimates. You can correct any of them before you save.')}</li>
            </ul>
          </Card>
          <Field
            label={t('log.meal.anything', "Anything the photo can't show? (optional)")}
            value={description}
            onChange={onDescription}
            multiline
            placeholder={t('log.meal.anythingPh', 'For example: only ate half the rice, no gravy, teh kosong')}
          />
          <TextLink onClick={onManual} icon={ForkKnife} className="self-start">
            {t('log.meal.byHandInstead', 'Enter the meal by hand instead')}
          </TextLink>
        </section>
      </Split>
      <Footer>
        <Button icon={ForkKnife} disabled={!preview} onClick={onRead}>
          {t('log.meal.analyse', 'Read my meal')}
        </Button>
      </Footer>
    </>
  )
}

/** The chosen photo with a "Change photo" button. Some browsers cannot show a photo they can still send, so a failed preview is said plainly. */
export function PhotoPreview({ src, onChange, changeLabel }: { src: string; onChange: () => void; changeLabel?: string }) {
  const { t } = useTranslation()
  const [failed, setFailed] = useState(false)
  return (
    <div className="relative overflow-hidden rounded-card border border-line bg-well">
      {failed ? (
        <p className="flex min-h-56 items-center justify-center p-6 text-center text-sub text-ink2">
          {t('log.meal.noPreview', 'This photo cannot be shown here, but it can still be read.')}
        </p>
      ) : (
        <img src={src} alt={t('log.meal.alt', 'Your meal')} className="max-h-80 w-full object-cover" onError={() => setFailed(true)} />
      )}
      <button type="button" onClick={onChange} className="press absolute right-3 top-3 min-h-12 rounded-chip bg-ink/80 px-4 text-sub font-bold text-canvas">
        {changeLabel ?? t('log.meal.changePhoto', 'Change photo')}
      </button>
    </div>
  )
}
