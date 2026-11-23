export function formatMiles(miles: number): string {
  return `${miles.toLocaleString(undefined, { maximumFractionDigits: 1 })} mi`
}

export function formatDuration(seconds: number): string {
  const minutes = Math.round(seconds / 60)
  const h = Math.floor(minutes / 60)
  const m = minutes % 60
  return h ? `${h} h ${m} min` : `${m} min`
}
