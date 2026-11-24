import { useMutation } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { apiErrorMessage, apiPost, isRetryable, planErrors } from '@/api/client'
import type { Plan, PlanRequest } from '@/api/types'
import { Alert } from '@/components/Alert'
import { EmptyState } from '@/components/EmptyState'
import { MapView } from '@/components/MapView'
import { PlanForm } from '@/components/PlanForm'
import { PlanSkeleton } from '@/components/PlanSkeleton'
import { RouteCards } from '@/components/RouteCards'
import { exampleRequest } from '@/lib/example'

export default function App() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const form = useRef<HTMLFormElement>(null)
  const [example, setExample] = useState<PlanRequest>()
  const plan = useMutation({
    mutationFn: (body: PlanRequest) => apiPost<Plan>('/api/plan', body),
    onSuccess: () => setSelectedId(null), // a new plan starts on its recommended route
  })
  const routeId = selectedId ?? plan.data?.recommended_route_id

  const errors = planErrors(plan.error)
  const noSafeRoute = plan.data?.routes.every((r) => r.summary.miles_by_level.no_travel > 0)

  function tryExample() {
    const body = exampleRequest()
    setExample(body)
    plan.mutate(body)
  }

  return (
    <main className="flex min-h-svh flex-col md:grid md:h-svh md:grid-cols-[22rem_1fr]">
      <aside className="flex flex-col gap-4 border-b p-4 md:overflow-y-auto md:border-r md:border-b-0">
        <h1 className="text-2xl font-semibold">Spotter</h1>
        {/* The key remounts the form pre-filled with the example. */}
        <PlanForm
          ref={form}
          key={example ? 'example' : 'blank'}
          initial={example}
          pending={plan.isPending}
          errors={errors}
          onSubmit={plan.mutate}
        />

        {plan.isIdle && <EmptyState onTryExample={tryExample} />}
        {plan.isPending && <PlanSkeleton />}
        {plan.isError && (
          // Retrying resubmits the form, so edits made since the failure count.
          <Alert tone="error" onRetry={isRetryable(plan.error) ? () => form.current?.requestSubmit() : undefined}>
            {Object.keys(errors).length ? 'Fix the highlighted fields, then plan again.' : apiErrorMessage(plan.error)}
          </Alert>
        )}
        {plan.data?.warnings.map((warning) => (
          <Alert key={warning} tone={noSafeRoute ? 'error' : 'warning'}>
            {warning}
          </Alert>
        ))}
        {plan.data && routeId && <RouteCards plan={plan.data} selectedId={routeId} onSelect={setSelectedId} />}
      </aside>
      <div className="h-[70svh] md:h-auto">
        <MapView planId={plan.data?.plan_id} routes={plan.data?.routes} selectedId={routeId} onSelectRoute={setSelectedId} />
      </div>
    </main>
  )
}
