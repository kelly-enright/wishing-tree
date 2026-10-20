import { useCallback, useEffect, useState } from 'react'
import { calendarUrl, getGranted, releasePledge, userMessage, type GrantedRow } from '../api'
import CategoryIcon from '../components/CategoryIcon'
import { MontySays } from '../components/Monty'

/**
 * What a donor has taken on.
 *
 * Carries the wish card and nothing else about the family — no name, no
 * address, no contact. The same wall of separation the family side keeps.
 */
export default function MyGranted({ alias }: { alias: string }) {
  const [rows, setRows] = useState<GrantedRow[] | null>(null)
  const [thisWeek, setThisWeek] = useState<GrantedRow[]>([])
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState<number | null>(null)

  const load = useCallback(() => {
    getGranted(alias)
      .then((data) => { setRows(data.granted); setThisWeek(data.this_week) })
      .catch((e) => setError(userMessage(e, 'We could not load what you have granted.')))
  }, [alias])

  useEffect(() => { load() }, [load])

  async function release(pledgeId: number) {
    setBusy(pledgeId)
    try {
      const result = await releasePledge(pledgeId, alias)
      setNote(result.message)
      load()
    } catch (e) {
      setError(userMessage(e, 'We could not release that just now.'))
    } finally {
      setBusy(null)
    }
  }

  if (error) return <p className="form__error">{error}</p>
  if (!rows) return <p className="activity__loading">Loading…</p>

  return (
    <>
      {thisWeek.length > 0 && (
        <section className="weekbanner" aria-label="Drop-off this week">
          <div>
            <p className="weekbanner__title">
              You have {thisWeek.length === 1 ? 'a drop-off' : `${thisWeek.length} drop-offs`} this week
            </p>
            <p className="weekbanner__detail">
              {thisWeek[0].dropoff_date} at {thisWeek[0].hub_name}, {thisWeek[0].dropoff_window}
            </p>
          </div>
          <a
            className="btn btn--light" download
            href={calendarUrl(thisWeek[0].pledge_id, alias)}
          >
            Add to calendar
          </a>
        </section>
      )}

      {note && <p className="sheet__note">{note}</p>}

      {rows.length === 0 && (
        <MontySays>
          You haven't granted anything yet. Have a look at the tree — Monty says
          the gold leaves are the ones already spoken for.
        </MontySays>
      )}

      {rows.length > 0 && (
        <section className="granted" aria-label="My granted wishes">
          <h2 className="granted__title">My granted wishes</h2>

          {rows.map((row) => (
            <article key={row.pledge_id} className={`gcard gcard--${row.status}`}>
              <header className="gcard__head">
                <span className={`track__stage track__stage--${row.status}`}>{row.label}</span>
                <CategoryIcon category={row.wish.category} size={16} />
              </header>

              <p className="gcard__item">{row.wish.item_description}</p>

              {!row.paid_directly_to_provider && row.status === 'pledged' && (
                <p className="gcard__when">
                  Drop off <strong>{row.dropoff_date}</strong>, {row.dropoff_window}<br />
                  {row.hub_name}, {row.hub_address}
                </p>
              )}

              {row.status === 'dropped_off' && (
                <p className="gcard__when">Delivered to the family on {row.delivery_date}.</p>
              )}

              <div className="gcard__actions">
                {row.can_release && !row.paid_directly_to_provider && (
                  <a className="btn btn--light btn--small" download
                     href={calendarUrl(row.pledge_id, alias)}>
                    Add to calendar
                  </a>
                )}
                {row.can_release && (
                  <button
                    type="button" className="btn btn--light btn--small"
                    disabled={busy === row.pledge_id}
                    onClick={() => release(row.pledge_id)}
                  >
                    I can't make it anymore
                  </button>
                )}
              </div>
            </article>
          ))}
        </section>
      )}
    </>
  )
}
