export function formatScheduleVariance(days) {
  if (days > 0.05) return `+${days.toFixed(1)}d late`
  if (days < -0.05) return `${Math.abs(days).toFixed(1)}d ahead`
  return 'On target'
}
