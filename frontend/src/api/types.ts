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

export type Route = {
  id: string
  distance_mi: number
  duration_s: number
  geometry: [lon: number, lat: number][]
  checkpoints: Checkpoint[]
}

export type Plan = { routes: Route[] }
