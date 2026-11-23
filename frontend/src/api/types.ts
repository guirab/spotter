// Mirrors the API contract in PLAN.md §5.3.
export type Place = { label: string; lat: number; lon: number }

export type Interval = 10 | 25 | 50

export type PlanRequest = {
  origin: Place
  destination: Place
  departure_at: string // UTC ISO-8601
  load_lb: number
  interval_mi: Interval
}

export type RiskLevel = 'low' | 'moderate' | 'high' | 'severe' | 'no_travel'

export type Weather = { wind_mph: number; gust_mph: number; rain_in_hr: number; snow_in_hr: number }

export type Checkpoint = {
  mile: number
  lat: number
  lon: number
  segment_mi: number
  eta: string // UTC ISO-8601
  weather: Weather // the forecast hour nearest the ETA
  level: RiskLevel
  score: number // 0 (Low) to 4 (No Travel)
  reasons: string[]
}

export type RouteSummary = {
  miles_by_level: Record<RiskLevel, number>
  avg_risk: number // distance-weighted mean score, 0–4
  max_level: RiskLevel
  first_hazard: { mile: number; eta: string; level: RiskLevel } | null // first checkpoint at High or worse
}

export type Route = {
  id: string
  rank: number // 1 = best
  distance_mi: number
  duration_s: number
  geometry: [lon: number, lat: number][]
  checkpoints: Checkpoint[]
  summary: RouteSummary
}

export type Plan = {
  plan_id: string // fetches the heatmap for an hour
  recommended_route_id: string
  recommendation_reason: string
  warnings: string[]
  routes: Route[] // sorted by rank
}

export type Heatmap = {
  start_at: string // UTC ISO-8601, the departure floored to the hour
  spacing_deg: number // lattice spacing, which sizes the heatmap radius
  points: [lon: number, lat: number][]
  scores: number[][] // per point, 49 hourly risk scores (0–4) from start_at
}
