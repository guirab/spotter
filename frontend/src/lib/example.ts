import type { PlanRequest } from '@/api/types'
import { nextFullHour } from '@/lib/format'

/** A long haul for the "Try an example" button; 42,000 lb is heavy enough for the load rules to apply. */
export function exampleRequest(): PlanRequest {
  return {
    origin: { label: 'Denver, CO', lat: 39.738453, lon: -104.984853 },
    destination: { label: 'Chicago, IL', lat: 41.8781, lon: -87.6298 },
    departure_at: nextFullHour().toISOString(),
    load_lb: 42_000,
    interval_mi: 25,
  }
}
