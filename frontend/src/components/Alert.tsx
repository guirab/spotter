import { CircleAlert, TriangleAlert } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

type Props = { tone: 'error' | 'warning'; children: ReactNode; onRetry?: () => void }

/** The inline banner for every error and warning, with an optional retry. */
export function Alert({ tone, children, onRetry }: Props) {
  const Icon = tone === 'error' ? CircleAlert : TriangleAlert
  return (
    <div
      role="alert"
      className={cn(
        'flex items-start gap-2 rounded-lg border p-3 text-sm',
        tone === 'error'
          ? 'border-destructive/40 bg-destructive/10 text-destructive'
          : 'border-amber-500/50 bg-amber-50 text-amber-950',
      )}
    >
      <Icon aria-hidden className="mt-0.5 size-4 shrink-0" />
      <p className="min-w-0 flex-1">{children}</p>
      {onRetry && (
        <Button type="button" variant="outline" size="sm" className="text-foreground" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  )
}
