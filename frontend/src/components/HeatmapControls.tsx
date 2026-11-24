import { apiErrorMessage, isRetryable } from '@/api/client'
import { Alert } from '@/components/Alert'
import { formatDateTime } from '@/lib/format'
import { RISK_LEVELS } from '@/lib/risk'

const HAZARD_LEVELS = (['moderate', 'high', 'severe', 'no_travel'] as const).map((level) => RISK_LEVELS[level])

type Props = {
  startAt?: string
  loading: boolean
  error: Error | null
  onRetry: () => void
  hour: number
  onHourChange: (hour: number) => void
  visible: boolean
  onVisibleChange: (visible: boolean) => void
}

export function HeatmapControls({ startAt, loading, error, onRetry, hour, onHourChange, visible, onVisibleChange }: Props) {
  if (loading) {
    return <p className="rounded-full bg-background/90 px-3 py-1 text-sm shadow">Loading weather corridor…</p>
  }
  if (error) {
    return (
      // The alert's tint sits on a solid background, so the map does not show through.
      <div className="w-full max-w-md rounded-lg bg-background shadow">
        <Alert tone="error" onRetry={isRetryable(error) ? onRetry : undefined}>
          {apiErrorMessage(error)}
        </Alert>
      </div>
    )
  }
  if (!startAt) return null
  const time = formatDateTime(new Date(Date.parse(startAt) + hour * 3_600_000).toISOString())

  return (
    <div className="flex w-full max-w-md flex-col gap-2 rounded-md bg-background/95 p-3 text-sm shadow">
      <div className="flex items-center justify-between gap-2">
        <label htmlFor="heatmap-hour" className="font-medium">
          Weather risk <span className="tabular-nums">+{hour} h</span> · {time}
        </label>
        <label className="flex items-center gap-1.5 text-muted-foreground">
          <input type="checkbox" checked={visible} onChange={(e) => onVisibleChange(e.target.checked)} />
          Show
        </label>
      </div>
      <input
        id="heatmap-hour"
        type="range"
        min={0}
        max={48}
        step={1}
        value={hour}
        aria-valuetext={`+${hour} h, ${time}`}
        onChange={(e) => onHourChange(e.target.valueAsNumber)}
        className="w-full accent-primary"
      />
      <ul className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
        {HAZARD_LEVELS.map(({ label, color }) => (
          <li key={label} className="flex items-center gap-1">
            <span aria-hidden className="size-2.5 rounded-full" style={{ backgroundColor: color }} />
            {label}
          </li>
        ))}
        <li>Colors appear from Moderate up; Low stays clear.</li>
      </ul>
    </div>
  )
}
