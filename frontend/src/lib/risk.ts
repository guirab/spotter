import type { ExpressionSpecification } from 'maplibre-gl'
import type { RiskLevel } from '@/api/types'

/** One label and color per level, used by every view; the label always goes next to the color. */
export const RISK_LEVELS: Record<RiskLevel, { label: string; color: string }> = {
  low: { label: 'Low', color: '#16a34a' },
  moderate: { label: 'Moderate', color: '#eab308' },
  high: { label: 'High', color: '#f97316' },
  severe: { label: 'Severe', color: '#dc2626' },
  no_travel: { label: 'No Travel', color: '#7e22ce' },
}

/** Heatmap density (score / 4) to the level hues. Density 0 is clear, so Low never shows: only hazards do. */
export const HEATMAP_COLOR: ExpressionSpecification = [
  'interpolate',
  ['linear'],
  ['heatmap-density'],
  0,
  `${RISK_LEVELS.moderate.color}00`,
  0.25,
  RISK_LEVELS.moderate.color,
  0.5,
  RISK_LEVELS.high.color,
  0.75,
  RISK_LEVELS.severe.color,
  1,
  RISK_LEVELS.no_travel.color,
]
