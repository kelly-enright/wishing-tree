import { CATEGORY_LABELS, OCCASION_LABELS, type WishCard as Wish } from '../api'
import CategoryIcon from './CategoryIcon'
import { ItemLink } from './ItemLink'
import { ShieldCheck, Sparkles } from 'lucide-react'
import { deadline as deadlineText } from '../dates'

function cost(wish: Wish): string {
  if (wish.budget_min_usd != null && wish.budget_max_usd != null) {
    return `$${wish.budget_min_usd.toFixed(0)}–$${wish.budget_max_usd.toFixed(0)}`
  }
  if (wish.estimated_cost_usd != null) return `$${wish.estimated_cost_usd.toFixed(0)}`
  if (wish.budget_max_usd != null) return `up to $${wish.budget_max_usd.toFixed(0)}`
  return '—'
}

/**
 * One wish as a wish granter sees it. Built from the card the server sends,
 * which has no contact details on it to begin with.
 *
 * Two tiers. Cost and deadline decide whether someone can help at all, so
 * they are the only things set large. Category, occasion, area and how long
 * a wish has waited are worth knowing and not worth a label each — they run
 * along one quiet line underneath.
 *
 * "Waiting 0 days" is not a fact anyone needs, so a wish that went up today
 * simply does not mention it.
 */
export default function WishCard({
  wish, reason, onGrant, granting, checked = true,
}: {
  wish: Wish
  reason?: string
  onGrant?: (wish: Wish) => void
  granting?: boolean
  /** False on the preview, where the Privacy & Safety agent has not run yet
   *  and the badge would be claiming something that has not happened. */
  checked?: boolean
}) {
  const urgent = wish.days_until_deadline != null && wish.days_until_deadline <= 7

  return (
    <article className={`card${urgent ? ' card--urgent' : ''}`}>
      <header className="card__head">
        <span className="card__kind">
          <CategoryIcon category={wish.category} size={15} />
          {wish.request_type === 'specific' ? 'Specific item' : 'Flexible need'}
        </span>
        <span className="card__alias">{wish.family_alias}</span>
      </header>

      {wish.badges && wish.badges.length > 0 && (
        <p className="card__badges">
          {wish.badges.map((badge) => (
            <span key={badge.kind} className={`badge badge--${badge.kind}`} title={badge.detail}>
              {badge.label}
            </span>
          ))}
        </p>
      )}

      <p className="card__desc">{wish.item_description}</p>

      {/* The Matchmaker's reasoning, attributed. A sentence that just appears
          on a card reads as marketing; the same sentence under a chip that
          says where it came from reads as the model showing its work. */}
      {reason && (
        <div className="why">
          <span className="why__chip">
            <Sparkles size={12} aria-hidden="true" />
            Why this match
          </span>
          <p className="why__text">{reason}</p>
        </div>
      )}

      <dl className="card__facts">
        <div><dt>Cost</dt><dd>
          {cost(wish)}
          {wish.cost_is_estimate && <span className="pill-estimate">Estimated</span>}
        </dd></div>
        <div><dt>Needed by</dt><dd>
          {wish.deadline ? deadlineText(wish.deadline) : 'No deadline'}
        </dd></div>
      </dl>

      <p className="card__meta">
        <span className="card__cat">
          <CategoryIcon category={wish.category} size={13} />
          {CATEGORY_LABELS[wish.category]}
        </span>
        <span>{OCCASION_LABELS[wish.occasion]}</span>
        <span>{wish.zip}</span>
        {wish.days_waiting > 0 && (
          <span>waiting {wish.days_waiting} day{wish.days_waiting === 1 ? '' : 's'}</span>
        )}
      </p>

      {/* "Size" is only the right word for a size. A preference note —
          "Partial help is still useful" — is not one, so it stands alone. */}
      {/* Every wish here has been through the Privacy & Safety agent — that
          is the only route to `open`. Saying so on the card is the quiet
          reassurance that makes a stranger's wish feel safe to read. */}
      {checked && (
        <p className="card__checked" title="A Privacy & Safety agent checked this wish for names, addresses and anything identifying before it went up.">
          <ShieldCheck size={12} aria-hidden="true" />
          Checked for privacy
        </p>
      )}

      {wish.size && <p className="card__extra">Size: {wish.size}</p>}
      {!wish.size && wish.size_preferences && (
        <p className="card__extra">{wish.size_preferences}</p>
      )}

      <div className="card__actions">
        {wish.product_link && <ItemLink href={wish.product_link} small />}
        {onGrant && (
          <button
            type="button" className="btn btn--gold card__grant"
            onClick={() => onGrant(wish)} disabled={granting}
          >
            {granting ? 'Granting…' : "I'll grant this wish"}
          </button>
        )}
      </div>
    </article>
  )
}
