import { useCallback, useEffect, useState } from 'react'
import { getMyWishes, respondToWindow, userMessage, type WishProgress } from '../api'
import { MontySays } from '../components/Monty'
import { when } from '../dates'
import { useToast } from '../components/Toast'
import { MontyInLeaves } from '../components/MontyPlays'
import { SkeletonRows } from '../components/Skeleton'

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
  const toast = useToast()
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
      toast(response === 'confirmed'
        ? 'Delivery confirmed'
        : 'Thanks — a coordinator will be in touch')
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
  if (!rows) {
    return (
      <section className="mywishes" id="mywishes" aria-label="My wishes">
        <h2 className="mywishes__title">My wishes</h2>
        <p className="sr-only" role="status">Loading your wishes…</p>
        <SkeletonRows count={2} />
      </section>
    )
  }

  if (rows.length === 0) {
    return (
      <MontySays mood="calm">
        <strong>Nothing posted yet.</strong><br />
        Start a chat below and tell us what would help. You'll see each wish here
        once it's up.
      </MontySays>
    )
  }

  const sorted = [...rows].sort((a, b) => ORDER.indexOf(a.stage) - ORDER.indexOf(b.stage))
  // The honest sentence about the tree is worth saying, and worth saying
  // once. Three wishes used to repeat it three times, which is how careful
  // wording starts reading like boilerplate.
  const anyOnTheTree = sorted.some((row) => row.stage === 'on_the_tree')

  return (
    <section className="mywishes" id="mywishes" aria-label="My wishes">
      <h2 className="mywishes__title">My wishes</h2>

      {anyOnTheTree && (
        <p className="mywishes__how">
          Wishes on the tree are where neighbors can see them. We can't promise
          someone will grant a wish, but we'll do our best to find a neighbor
          who can help.
        </p>
      )}

      {sorted.map((row) => (
        <article key={row.wish.id} className={`track track--${row.stage}`}>
          <header className="track__head">
            <span className={`track__stage track__stage--${row.stage}`}>{row.label}</span>
            {row.still_looking && (
              <span className="track__again">back on the tree</span>
            )}
          </header>

          {/* A wish that has arrived is the moment the whole app is for. */}
          {row.stage === 'delivered' && (
            <MontyInLeaves size={52} replay={row.wish.id} />
          )}
          <p className="track__item">{row.wish.item_description}</p>
          {row.stage !== 'on_the_tree' && <p className="track__detail">{row.detail}</p>}

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
                Delivery on <strong>{when(row.delivery.date, row.delivery.window)}</strong>.
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
