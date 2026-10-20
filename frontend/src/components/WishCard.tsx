import { CATEGORY_LABELS, OCCASION_LABELS, type WishCard as Wish } from '../api'

function cost(wish: Wish): string {
  if (wish.budget_min_usd != null && wish.budget_max_usd != null) {
    return `$${wish.budget_min_usd.toFixed(0)}–$${wish.budget_max_usd.toFixed(0)}`
  }
  if (wish.estimated_cost_usd != null) return `$${wish.estimated_cost_usd.toFixed(0)}`
  if (wish.budget_max_usd != null) return `up to $${wish.budget_max_usd.toFixed(0)}`
  return '—'
}

/** One wish as a donor sees it. Built from the card the server sends, which
 *  has no contact details on it to begin with. */
export default function WishCard({
  wish, reason, onGrant, granting,
}: {
  wish: Wish
  reason?: string
  onGrant?: (wish: Wish) => void
  granting?: boolean
}) {
  const urgent = wish.days_until_deadline != null && wish.days_until_deadline <= 7

  return (
    <article className={`card${urgent ? ' card--urgent' : ''}`}>
      <header className="card__head">
        <span className="card__kind">
          {wish.request_type === 'specific' ? 'Specific item' : 'Flexible need'}
        </span>
        <span className="card__alias">{wish.family_alias}</span>
      </header>

      <p className="card__desc">{wish.item_description}</p>

      {reason && <p className="card__reason">{reason}</p>}

      <dl className="card__facts">
        <div><dt>Cost</dt><dd>
          {cost(wish)}
          {wish.cost_is_estimate && <span className="pill-estimate">Estimated</span>}
        </dd></div>
        <div><dt>Needed by</dt><dd>
          {wish.deadline_label}
          {wish.days_until_deadline != null && (
            <span className="card__days">
              {wish.days_until_deadline < 0
                ? ` (${Math.abs(wish.days_until_deadline)}d ago)`
                : ` (${wish.days_until_deadline}d)`}
            </span>
          )}
        </dd></div>
        <div><dt>Category</dt><dd>{CATEGORY_LABELS[wish.category]}</dd></div>
        <div><dt>Occasion</dt><dd>{OCCASION_LABELS[wish.occasion]}</dd></div>
        <div><dt>Area</dt><dd>{wish.zip}</dd></div>
        <div><dt>Waiting</dt><dd>{wish.days_waiting} day{wish.days_waiting === 1 ? '' : 's'}</dd></div>
      </dl>

      {(wish.size || wish.size_preferences) && (
        <p className="card__extra">Size: {wish.size ?? wish.size_preferences}</p>
      )}
      {wish.product_link && (
        <p className="card__extra card__link">{wish.product_link}</p>
      )}

      {onGrant && (
        <button
          type="button" className="btn btn--gold card__grant"
          onClick={() => onGrant(wish)} disabled={granting}
        >
          {granting ? 'Granting…' : 'Grant this wish'}
        </button>
      )}
    </article>
  )
}
