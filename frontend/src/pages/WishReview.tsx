import { CATEGORY_LABELS, OCCASION_LABELS, type Category, type DraftWish, type Occasion } from '../api'

/** The approval screen: the family edits, deletes or approves each wish. */
export default function WishReview({
  wishes,
  onChange,
  onRemove,
  onApprove,
  busy,
  error,
}: {
  wishes: DraftWish[]
  onChange: (index: number, patch: Partial<DraftWish>) => void
  onRemove: (index: number) => void
  onApprove: () => void
  busy: boolean
  error: string | null
}) {
  if (wishes.length === 0) {
    return (
      <div className="review">
        <p className="review__empty">
          No wishes yet. Go back to the chat and tell us a bit more about what you need.
        </p>
      </div>
    )
  }

  return (
    <div className="review">
      <p className="review__intro">
        Check each one before it goes anywhere. Change anything that isn’t right, remove
        what you don’t want, then approve. Nothing is public until it has been reviewed.
      </p>

      {wishes.map((wish, index) => (
        <article className="wish" key={index}>
          <header className="wish__head">
            <span className="wish__kind">
              {wish.request_type === 'specific' ? 'Specific item' : 'Flexible need'}
            </span>
            <button type="button" className="wish__remove" onClick={() => onRemove(index)}>
              Remove
            </button>
          </header>

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

          {wish.product_link && (
            <p className="wish__link">
              Link: <span>{wish.product_link}</span>
            </p>
          )}
        </article>
      ))}

      {error && <p className="form__error" role="alert">{error}</p>}

      <button className="btn btn--primary" type="button" onClick={onApprove} disabled={busy}>
        {busy ? 'Submitting…' : `Approve ${wishes.length} wish${wishes.length === 1 ? '' : 'es'}`}
      </button>
      <p className="review__note">
        Approved wishes go for a privacy and safety review before anyone sees them.
      </p>
    </div>
  )
}
