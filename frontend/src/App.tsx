import { useMutation } from '@tanstack/react-query'
import { apiErrorMessage, apiPost } from '@/api/client'
import type { Plan, PlanRequest } from '@/api/types'
import { MapView } from '@/components/MapView'
import { PlanForm } from '@/components/PlanForm'
import { formatDuration, formatMiles } from '@/lib/format'

export default function App() {
  const plan = useMutation({ mutationFn: (body: PlanRequest) => apiPost<Plan>('/api/plan', body) })
  const route = plan.data?.routes[0]

  return (
    <main className="flex h-svh flex-col md:grid md:grid-cols-[22rem_1fr]">
      <aside className="flex flex-col gap-4 overflow-y-auto border-b p-4 md:border-r md:border-b-0">
        <h1 className="text-2xl font-semibold">Spotter</h1>
        <PlanForm pending={plan.isPending} onSubmit={plan.mutate} />

        {plan.isError && (
          <p role="alert" className="text-sm text-destructive">
            {apiErrorMessage(plan.error)}
          </p>
        )}

        {route && (
          <dl className="grid grid-cols-2 gap-2 text-sm">
            <dt className="text-muted-foreground">Distance</dt>
            <dd>{formatMiles(route.distance_mi)}</dd>
            <dt className="text-muted-foreground">Duration</dt>
            <dd>{formatDuration(route.duration_s)}</dd>
          </dl>
        )}
      </aside>
      <div className="min-h-[60svh] flex-1">
        <MapView route={route} />
      </div>
    </main>
  )
}
