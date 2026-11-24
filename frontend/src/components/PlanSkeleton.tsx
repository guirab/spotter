import { useEffect, useState } from 'react'

const WEATHER_HINT_MS = 3000 // roughly when routing ends; the API reports no progress

/** Placeholder route cards and a progress hint while the plan is computed. */
export function PlanSkeleton() {
  const [checkingWeather, setCheckingWeather] = useState(false)
  useEffect(() => {
    const timer = setTimeout(() => setCheckingWeather(true), WEATHER_HINT_MS)
    return () => clearTimeout(timer)
  }, [])

  return (
    <section className="flex flex-col gap-3" aria-label="Planning">
      <p role="status" className="text-sm text-muted-foreground">
        {checkingWeather ? 'Checking the weather along each route…' : 'Finding truck routes…'}
      </p>
      {['A', 'B', 'C'].map((id) => (
        <div key={id} aria-hidden className="flex animate-pulse flex-col gap-3 rounded-lg border p-3 motion-reduce:animate-none">
          <div className="h-4 w-24 rounded bg-muted" />
          <div className="h-3 w-3/4 rounded bg-muted" />
          <div className="h-3 w-2/3 rounded bg-muted" />
          <div className="h-3 w-1/2 rounded bg-muted" />
          <div className="h-2 w-full rounded-full bg-muted" />
        </div>
      ))}
    </section>
  )
}
