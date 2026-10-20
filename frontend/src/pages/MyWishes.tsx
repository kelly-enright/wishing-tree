import { useCallback, useEffect, useState } from 'react'
import { getMyWishes, respondToWindow, userMessage, type WishProgress } from '../api'

const ORDER: WishProgress['stage'][] = [
  'granted', 'on_its_way', 'being_checked', 'on_the_tree', 'not_posted', 'delivered',
]

/**
 * Where a family follows what happened to each wish.
 *
 * Nothing here mentions a donor. A family sees the state of their own wish and
 * the date it arrives; who granted it is not theirs to know, and a donor who
 * drops out should not become a person a family is waiting on by name.
 */
export default function MyWishes({ alias }: { alias: string }) {
  const [rows, setRows] = useState<WishProgress[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<number | null>(null)
  const [notes, setNotes] = useState<Record<number, string>>({})

  const load = useCallback(() => {
    getMyWishes(alias)
      .then((data) => setRows(data.wishes))
      .catch((e) => setError(userMessage(e, 'We could not load your wishes just now.')))
  }, [alias])

  useEffect(() => { load() }, [load])

  async function answer(pledgeId: number, response: 'confirmed' | 'needs_reschedule') {
    setBusy(pledgeId)
    try {
      const result = await respondToWindow(alias, pledgeId, response)
      setNotes((n) => ({ ...n, [pledgeId]: result.message }))
      load()
    } catch (e) {
      setNotes((n) => ({
        ...n,
        [pledgeId]: userMessage(e, 'We could not save that just now. Please try again.'),
      }))
    } finally {
      setBusy(null)
    }
  }

  if (error) return <p className="form__error">{error}</p>
  if (!rows) return <p className="activity__loading">Loading your wishes…</p>

  if (rows.length === 0) {
    return (
      <div className="mywishes__empty">
        <p className="mywishes__empty-title">Nothing posted yet</p>
        <p>
          Start a chat below and tell us what would help. You'll see each wish here
          once it's up.
        </p>
      </div>
    )
  }

  const sorted = [...rows].sort((a, b) => ORDER.indexOf(a.stage) - ORDER.indexOf(b.stage))

  return (
    <section className="mywishes" aria-label="My wishes">
      <h2 className="mywishes__title">My wishes</h2>

      {sorted.map((row) => (
        <article key={row.wish.id} className={`track track--${row.stage}`}>
          <header className="track__head">
            <span className={`track__stage track__stage--${row.stage}`}>{row.label}</span>
            {row.still_looking && (
              <span className="track__again">back on the tree</span>
            )}
          </header>

          <p className="track__item">{row.wish.item_description}</p>
          <p className="track__detail">{row.detail}</p>

          {row.direct_payment && row.direct_payment_note && (
            <p className="track__rent">{row.direct_payment_note}</p>
          )}

          {row.removed_before_posting.length > 0 && (
            <p className="track__removed">
              Taken out before anyone saw it: {row.removed_before_posting.join(', ')}.
            </p>
          )}

          {row.delivery && (
            <div className="track__delivery">
              <p>
                Delivery on <strong>{row.delivery.date}</strong>, {row.delivery.window}.
              </p>

              {row.delivery.window_response === 'pending' && (
                <div className="delivery__actions">
                  <button
                    type="button" className="btn btn--primary btn--small"
                    disabled={busy === row.delivery.pledge_id}
                    onClick={() => answer(row.delivery!.pledge_id, 'confirmed')}
                  >
                    Confirm delivery window
                  </button>
                  <button
                    type="button" className="btn btn--light btn--small"
                    disabled={busy === row.delivery.pledge_id}
                    onClick={() => answer(row.delivery!.pledge_id, 'needs_reschedule')}
                  >
                    This doesn’t work
                  </button>
                </div>
              )}

              {row.delivery.window_response === 'confirmed' && (
                <p className="delivery__confirmed">You confirmed this window.</p>
              )}
              {row.delivery.window_response === 'needs_reschedule' && (
                <p className="delivery__flagged">
                  A coordinator will reach out to reschedule.
                </p>
              )}
              {notes[row.delivery.pledge_id] && (
                <p className="delivery__message">{notes[row.delivery.pledge_id]}</p>
              )}
            </div>
          )}
        </article>
      ))}
    </section>
  )
}
