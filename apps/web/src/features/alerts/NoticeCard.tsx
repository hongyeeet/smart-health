import type { ReactNode } from 'react'
import { StatusPill, TextLink } from '@/ui/primitives'
import { CaretRight, type IconType } from '@/ui/icons'
import { cn } from '@/lib/cn'

/**
 * One notice, the same shape wherever it appears (the Meds page and the bell page): a coloured edge, a tag with its icon, the time, a
 * serif title, a little body, and one underlined green link at the bottom that opens the details. The edge and the tag carry the kind
 * (a medicine review is amber, a refill reminder is blue); the words say it too, so it never rests on colour alone.
 */
export function NoticeCard({
  tone,
  tag,
  icon,
  when,
  title,
  link,
  onLink,
  children,
}: {
  tone: 'warn' | 'info'
  tag: string
  icon: IconType
  when?: string
  title: string
  link?: string
  onLink?: () => void
  children?: ReactNode
}) {
  return (
    <article className="relative overflow-hidden rounded-card border border-line bg-card shadow-lift">
      <span className={cn('absolute inset-y-0 left-0 w-1.5', tone === 'warn' ? 'bg-warn' : 'bg-info')} aria-hidden />
      <div className="flex flex-col gap-3 p-4 pl-5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <StatusPill tone={tone} icon={icon}>
            {tag}
          </StatusPill>
          {when && <span className="text-sub text-ink3">{when}</span>}
        </div>
        <h2 className="font-serif text-h2 font-medium tracking-tight text-ink">{title}</h2>
        {children}
        {link && onLink && (
          <TextLink onClick={onLink} className="self-start text-left">
            {link}
            <CaretRight size={16} weight="bold" aria-hidden />
          </TextLink>
        )}
      </div>
    </article>
  )
}
