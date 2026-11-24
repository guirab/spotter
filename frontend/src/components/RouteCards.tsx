import type { Plan, RiskLevel, Route } from '@/api/types'
import { formatDateTime, formatDuration, formatMiles } from '@/lib/format'
import { RISK_LEVELS } from '@/lib/risk'
import { cn } from '@/lib/utils'

type Props = { plan: Plan; selectedId: string; onSelect: (id: string) => void }

/** One card per route, best first, with the recommendation. */
export function RouteCards({ plan, selectedId, onSelect }: Props) {
  return (
    <section className="flex flex-col gap-3" aria-label="Routes">
      {plan.routes.map((route) => (
        <RouteCard
          key={route.id}
          route={route}
          reason={route.id === plan.recommended_route_id ? plan.recommendation_reason : undefined}
          selected={route.id === selectedId}
          onSelect={() => onSelect(route.id)}
        />
      ))}
    </section>
  )
}

function RouteCard({
  route,
  reason,
  selected,
  onSelect,
}: {
  route: Route
  reason?: string
  selected: boolean
  onSelect: () => void
}) {
  const { summary } = route
  const arrival = route.checkpoints.at(-1)?.eta
  const levels = (Object.keys(RISK_LEVELS) as RiskLevel[]).filter((level) => summary.miles_by_level[level] > 0)

  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onSelect}
      className={cn(
        'flex flex-col gap-2 rounded-lg border p-3 text-left text-sm transition-colors hover:bg-muted/50',
        selected && 'border-[#1e3a8a] ring-1 ring-[#1e3a8a]',
      )}
    >
      <div className="flex items-center gap-2">
        <span className="font-semibold">Route {route.id}</span>
        {reason && (
          <span className="rounded-full bg-[#1e3a8a] px-2 py-0.5 text-xs font-medium text-white">Recommended</span>
        )}
      </div>
      {reason && <p className="text-muted-foreground">{reason}</p>}

      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-0.5">
        <dt className="text-muted-foreground">Distance</dt>
        <dd>{formatMiles(route.distance_mi)}</dd>
        <dt className="text-muted-foreground">Duration</dt>
        <dd>{formatDuration(route.duration_s)}</dd>
        {arrival && (
          <>
            <dt className="text-muted-foreground">Arrival</dt>
            <dd>{formatDateTime(arrival)}</dd>
          </>
        )}
        <dt className="text-muted-foreground">Avg risk</dt>
        <dd>{summary.avg_risk.toFixed(2)} / 4</dd>
        <dt className="text-muted-foreground">First hazard</dt>
        <dd>
          {summary.first_hazard
            ? `${RISK_LEVELS[summary.first_hazard.level].label} at ${formatMiles(summary.first_hazard.mile)}, ${formatDateTime(summary.first_hazard.eta)}`
            : 'None'}
        </dd>
      </dl>

      {/* Stacked bar of miles by level; the list below carries the same values as text. */}
      <div aria-hidden className="flex h-2 overflow-hidden rounded-full bg-muted">
        {levels.map((level) => (
          <div
            key={level}
            style={{ flexGrow: summary.miles_by_level[level], backgroundColor: RISK_LEVELS[level].color }}
          />
        ))}
      </div>
      <ul className="flex flex-wrap gap-x-3 text-xs text-muted-foreground">
        {levels.map((level) => (
          <li key={level}>
            {RISK_LEVELS[level].label} {formatMiles(summary.miles_by_level[level])}
          </li>
        ))}
      </ul>
    </button>
  )
}
