import { useEffect, useState } from 'react'
import {
  CATEGORY_LABELS, OCCASION_LABELS, getRetailers, linkIsAccepted,
  type Category, type DraftWish, type Occasion, type WishCard as Card,
} from '../api'
import WishCard from '../components/WishCard'

/**
 * The preview before anything is posted.
 *
 * Each wish is shown as the exact card a donor will see, so a family can
 * check what is being shared rather than trusting a description of it. The
 * editable fields sit behind "Make a change", because the point of this
 * screen is reading, not filling in a form again.
 */

function asCard(draft: DraftWish, index: number, alias: string): Card {
  const deadline = draft.deadline
  const days = deadline
    ? Math.round((new Date(deadline).getTime() - Date.now()) / 86_400_000)
    : null
  return {
    id: -1 - index,
    family_alias: alias,
    category: draft.category,
    occasion: draft.occasion,
    request_type: draft.request_type,
    item_description: draft.item_description,
    zip: '',
    deadline,
    deadline_label: deadline ?? 'No deadline',
    days_until_deadline: days,
    days_waiting: 0,
    estimated_cost_usd: draft.estimated_cost_usd,
    budget_min_usd: draft.budget_min_usd,
    budget_max_usd: draft.budget_max_usd,
    cost_ceiling_usd: draft.budget_max_usd ?? draft.estimated_cost_usd ?? 0,
    // Marked "Estimated" when the number came from the price guide rather
    // than from the family.
    cost_is_estimate:
      draft.estimated_cost_usd == null &&
      draft.budget_min_usd != null &&
      !draft.size,
    product_link: draft.product_link,
    brand: draft.brand,
    size: draft.size,
    color: draft.color,
    open_to_substitute: draft.open_to_substitute,
    size_preferences: draft.size_preferences,
    status: 'open',
  }
}

export default function WishReview({
  wishes, alias, onChange, onRemove, onApprove, onBack, busy, error,
}: {
  wishes: DraftWish[]
  alias: string
  onChange: (index: number, patch: Partial<DraftWish>) => void
  onRemove: (index: number) => void
  onApprove: () => void
  onBack: () => void
  busy: boolean
  error: string | null
}) {
  const [editing, setEditing] = useState<number | null>(null)
  const [stores, setStores] = useState<string[]>([])

  useEffect(() => {
    getRetailers().then((r) => setStores(r.stores)).catch(() => setStores([]))
  }, [])

  if (wishes.length === 0) {
    return (
      <div className="review">
        <p className="review__empty">
          No wishes yet. Go back to the chat and tell us a bit more about what you need.
        </p>
      </div>
    )
  }

  const count = wishes.length
  // A wish has a cost if it carries a single figure or a range.
  const missingCost = wishes.filter(
    (w) => w.estimated_cost_usd == null
      && (w.budget_min_usd == null || w.budget_max_usd == null),
  )

  return (
    <div className="review">
      <p className="review__intro">
        This is exactly what a neighbor will see — no names, no address, nothing
        that points back to you. Have a read, change anything that isn't right, and
        post when you're happy.
      </p>

      {wishes.map((wish, index) => {
        const linkOk = linkIsAccepted(wish.product_link ?? '', stores)
        return (
          <article className="preview" key={index}>
            <header className="preview__head">
              <span className="preview__eyebrow">What a neighbor will see</span>
              <button type="button" className="wish__remove" onClick={() => onRemove(index)}>
                Remove
              </button>
            </header>

            <WishCard wish={asCard(wish, index, alias)} checked={false} />

            {wish.category === 'rent_utilities' && (
              <p className="preview__rent">
                A coordinator will email you to confirm the amount and who to pay.
                The payment goes straight to your landlord or the utility company —
                never to you, and never through this app.
              </p>
            )}

            <button
              type="button" className="btn btn--light btn--small preview__toggle"
              onClick={() => setEditing(editing === index ? null : index)}
            >
              {editing === index ? 'Done changing' : 'Make a change'}
            </button>

            {editing === index && (
              <div className="preview__edit">
                <label className="field">
                  <span className="field__label">What is needed</span>
                  <textarea
                    className="field__input" rows={2} maxLength={400}
                    value={wish.item_description}
                    onChange={(e) => onChange(index, { item_description: e.target.value })}
                  />
                </label>

                <div className="wish__row">
                  <label className="field">
                    <span className="field__label">Category</span>
                    <select
                      className="field__input" value={wish.category}
                      onChange={(e) => onChange(index, { category: e.target.value as Category })}
                    >
                      {(Object.keys(CATEGORY_LABELS) as Category[]).map((c) => (
                        <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
                      ))}
                    </select>
                  </label>
                  <label className="field">
                    <span className="field__label">Occasion</span>
                    <select
                      className="field__input" value={wish.occasion}
                      onChange={(e) => onChange(index, { occasion: e.target.value as Occasion })}
                    >
                      {(Object.keys(OCCASION_LABELS) as Occasion[]).map((o) => (
                        <option key={o} value={o}>{OCCASION_LABELS[o]}</option>
                      ))}
                    </select>
                  </label>
                </div>

                <div className="wish__row">
                  <label className="field">
                    <span className="field__label">Needed by</span>
                    <input
                      className="field__input" type="date" value={wish.deadline ?? ''}
                      onChange={(e) => onChange(index, { deadline: e.target.value || null })}
                    />
                    <span className="field__hint">
                      {wish.deadline ? 'A donor will see this date.' : 'No deadline — add one only if a date matters.'}
                    </span>
                  </label>
                  <label className="field">
                    <span className="field__label">Size (if it matters)</span>
                    <input
                      className="field__input" value={wish.size ?? ''} placeholder="Boys 8"
                      onChange={(e) => onChange(index, { size: e.target.value || null })}
                    />
                  </label>
                </div>

                <div className="wish__row">
                  <label className="field">
                    <span className="field__label">Roughly costs</span>
                    <input
                      className="field__input" type="number" min="0" step="5"
                      value={wish.estimated_cost_usd ?? ''} placeholder="—"
                      onChange={(e) => onChange(index, {
                        estimated_cost_usd: e.target.value === '' ? null : Number(e.target.value),
                      })}
                    />
                  </label>
                  <label className="field">
                    <span className="field__label">Or a range, from</span>
                    <input
                      className="field__input" type="number" min="0" step="5"
                      value={wish.budget_min_usd ?? ''} placeholder="—"
                      onChange={(e) => onChange(index, {
                        budget_min_usd: e.target.value === '' ? null : Number(e.target.value),
                      })}
                    />
                  </label>
                  <label className="field">
                    <span className="field__label">to</span>
                    <input
                      className="field__input" type="number" min="0" step="5"
                      value={wish.budget_max_usd ?? ''} placeholder="—"
                      onChange={(e) => onChange(index, {
                        budget_max_usd: e.target.value === '' ? null : Number(e.target.value),
                      })}
                    />
                  </label>
                </div>
                <p className="wish__hint">
                  Leave the cost empty and we'll show a typical price for this category,
                  marked as an estimate. You can type over it.
                </p>

                <label className="field">
                  <span className="field__label">
                    Have a specific item in mind? Paste the link <em>(optional)</em>
                  </span>
                  <input
                    className="field__input" type="url" value={wish.product_link ?? ''}
                    placeholder="https://www.target.com/p/..."
                    onChange={(e) => onChange(index, {
                      product_link: e.target.value || null,
                      request_type: e.target.value ? 'specific' : 'flexible',
                    })}
                  />
                  <span className="field__hint">
                    We can post links from {stores.slice(0, 6).join(', ')} and{' '}
                    {Math.max(0, stores.length - 6)} other stores.
                  </span>
                </label>

                {!linkOk && (
                  <p className="preview__linknote">
                    We can't post a link from that site — but that's no problem. Leave
                    it out and a neighbor will pick something that fits your
                    description.
                  </p>
                )}
              </div>
            )}
          </article>
        )
      })}

      {error && <p className="form__error" role="alert">{error}</p>}

      {/* A wish with no cost cannot be granted: a neighbor reading the tree
          has no idea what they are taking on, so it would sit there. Better
          to ask for a number here, where it takes a second, than to post
          something nobody can act on. */}
      {missingCost.length > 0 && (
        <p className="review__needs" role="alert">
          {missingCost.length === 1
            ? 'One wish still needs a cost — a rough estimate is fine, and a neighbor can see what they are taking on.'
            : `${missingCost.length} wishes still need a cost — a rough estimate is fine for each.`}
        </p>
      )}

      <div className="review__actions">
        <button
          className="btn btn--gold" type="button" onClick={onApprove}
          disabled={busy || missingCost.length > 0}
          title={missingCost.length > 0 ? 'Add a cost to every wish first' : undefined}
        >
          {busy
            ? 'Posting…'
            : count === 1 ? 'Looks right, post my wish' : `Post my ${count} wishes`}
        </button>
        <button className="btn btn--light" type="button" onClick={onBack} disabled={busy}>
          Go back to the chat
        </button>
      </div>
      <p className="review__note">
        We'll check it for privacy before anyone sees it.
      </p>
    </div>
  )
}
