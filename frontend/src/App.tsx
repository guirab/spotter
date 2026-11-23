import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { apiErrorMessage, apiPost } from '@/api/client'
import type { Plan, PlanRequest } from '@/api/types'
import { MapView } from '@/components/MapView'
import { PlanForm } from '@/components/PlanForm'
import { RouteCards } from '@/components/RouteCards'

export default function App() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const plan = useMutation({
    mutationFn: (body: PlanRequest) => apiPost<Plan>('/api/plan', body),
    onSuccess: () => setSelectedId(null), // a new plan starts on its recommended route
  })
  const routeId = selectedId ?? plan.data?.recommended_route_id

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

        {plan.data && routeId && <RouteCards plan={plan.data} selectedId={routeId} onSelect={setSelectedId} />}
      </aside>
      <div className="min-h-[60svh] flex-1">
        <MapView planId={plan.data?.plan_id} routes={plan.data?.routes} selectedId={routeId} onSelectRoute={setSelectedId} />
      </div>
    </main>
  )
}
