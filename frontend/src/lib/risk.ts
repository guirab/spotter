import type { RiskLevel } from '@/api/types'

/** One label and color per level, used by every view; the label always goes next to the color. */
export const RISK_LEVELS: Record<RiskLevel, { label: string; color: string }> = {
  low: { label: 'Low', color: '#16a34a' },
  moderate: { label: 'Moderate', color: '#eab308' },
  high: { label: 'High', color: '#f97316' },
  severe: { label: 'Severe', color: '#dc2626' },
  no_travel: { label: 'No Travel', color: '#7e22ce' },
}
