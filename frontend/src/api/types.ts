// Mirrors the API contract in PLAN.md §5.3.
export type Place = { label: string; lat: number; lon: number }

export type PlanRequest = { origin: Place; destination: Place }

export type Route = {
  id: string
  distance_mi: number
  duration_s: number
  geometry: [lon: number, lat: number][]
}

export type Plan = { routes: Route[] }
