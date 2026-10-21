/**
 * What a wish costs, said the same way everywhere.
 *
 * A range when the family gave one, a single number when the price guide
 * estimated it, "up to" when only a ceiling is known, and an em dash when
 * nobody has put a number on it yet. Shared rather than copied, because a
 * neighbor and a wish granter looking at the same wish should see the same
 * figure written the same way.
 */
export function costLabel(wish: {
  budget_min_usd: number | null
  budget_max_usd: number | null
  estimated_cost_usd: number | null
}): string {
  if (wish.budget_min_usd != null && wish.budget_max_usd != null) {
    return `$${wish.budget_min_usd.toFixed(0)}–$${wish.budget_max_usd.toFixed(0)}`
  }
  if (wish.estimated_cost_usd != null) return `$${wish.estimated_cost_usd.toFixed(0)}`
  if (wish.budget_max_usd != null) return `up to $${wish.budget_max_usd.toFixed(0)}`
  return '—'
}
