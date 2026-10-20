import { useCallback, useEffect, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { calendarUrl, getGranted, releasePledge, userMessage, type GrantedRow } from '../api'
import CategoryIcon from '../components/CategoryIcon'
import { MontySays } from '../components/Monty'
import { ItemLink, MapLink } from '../components/ItemLink'
import { longDay, when } from '../dates'

/**
 * What a wish granter has taken on.
 *
 * Two sections, because they answer two different questions. "Coming up" is
 * the one with something left to do — a date to keep, a thing to buy, a
 * drop-off to make — so it is open at the top. "Wishes you've granted" is a
 * record of finished things, worth having and not worth scrolling past every
 * visit, so it starts collapsed.
 *
 * A wish released or missed appears in neither: it went back on the tree for
 * another neighbor, and the server has already dropped it from this payload.
 *
 * Carries the wish card and nothing else about the neighbor — no name, no
 * address, no contact. The same wall of separation the other side keeps.
 */
export default function MyGranted({ alias }: { alias: string }) {
  const [comingUp, setComingUp] = useState<GrantedRow[] | null>(null)
  const [done, setDone] = useState<GrantedRow[]>([])
  const [thisWeek, setThisWeek] = useState<GrantedRow[]>([])
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState<number | null>(null)
  const [showDone, setShowDone] = useState(false)

  const load = useCallback(() => {
    getGranted(alias)
      .then((data) => {
        setComingUp(data.coming_up)
        setDone(data.already_granted)
        setThisWeek(data.this_week)
      })
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
  if (!comingUp) return <p className="activity__loading">Loading…</p>

  const nothingYet = comingUp.length === 0 && done.length === 0

  return (
    <>
      {thisWeek.length > 0 && (
        <section className="weekbanner" aria-label="Drop-off this week">
          <div>
            <p className="weekbanner__title">
              You have {thisWeek.length === 1 ? 'a drop-off' : `${thisWeek.length} drop-offs`} this week
            </p>
            <p className="weekbanner__detail">
              {when(thisWeek[0].dropoff_date, thisWeek[0].dropoff_window)} at{' '}
              {thisWeek[0].hub_name}
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

      {nothingYet && (
        <MontySays>
          You haven't granted a wish yet. Have a look at the tree — Monty says
          the gold leaves are the ones already granted.
        </MontySays>
      )}

      {comingUp.length > 0 && (
        <section className="granted" aria-label="Coming up">
          <h2 className="granted__title">Coming up</h2>
          {comingUp.map((row) => (
            <Card key={row.pledge_id} row={row} alias={alias}
                  busy={busy === row.pledge_id} onRelease={release} />
          ))}
        </section>
      )}

      {done.length > 0 && (
        <section className="granted" aria-label="Wishes you've granted">
          <button
            type="button"
            className={`granted__toggle${showDone ? ' granted__toggle--open' : ''}`}
            aria-expanded={showDone}
            onClick={() => setShowDone((open) => !open)}
          >
            <ChevronDown size={16} aria-hidden="true" />
            <span className="granted__title">Wishes you've granted</span>
            <span className="granted__count">{done.length}</span>
          </button>

          {showDone && done.map((row) => (
            <Card key={row.pledge_id} row={row} alias={alias}
                  busy={busy === row.pledge_id} onRelease={release} />
          ))}
        </section>
      )}
    </>
  )
}

function Card({
  row, alias, busy, onRelease,
}: {
  row: GrantedRow; alias: string; busy: boolean; onRelease: (id: number) => void
}) {
  const direct = row.paid_directly_to_provider
  return (
    <article className={`gcard gcard--${row.status}`}>
      <header className="gcard__head">
        <span className={`track__stage track__stage--${row.status}`}>{row.label}</span>
        <CategoryIcon category={row.wish.category} size={16} />
      </header>

      <p className="gcard__item">{row.wish.item_description}</p>

      {!direct && row.status === 'pledged' && (
        <p className="gcard__when">
          Drop off <strong>{when(row.dropoff_date, row.dropoff_window)}</strong><br />
          <MapLink href={row.hub_maps_url}>
            {row.hub_name}, {row.hub_address}
          </MapLink>
        </p>
      )}

      {direct && row.status === 'pledged' && (
        <p className="gcard__when">
          A coordinator will email you the amount and who to pay. The payment
          goes straight to the landlord or the utility company.
        </p>
      )}

      {row.status === 'dropped_off' && !direct && (
        <p className="gcard__when">Delivered on {longDay(row.delivery_date)}.</p>
      )}

      {row.status === 'delivered' && (
        <p className="gcard__when">
          {direct ? 'Paid on ' : 'Arrived on '}{longDay(row.delivery_date)}.
        </p>
      )}

      <div className="gcard__actions">
        {row.wish.product_link && row.status === 'pledged' && (
          <ItemLink href={row.wish.product_link} small />
        )}
        {row.can_release && !direct && (
          <a className="btn btn--light btn--small" download
             href={calendarUrl(row.pledge_id, alias)}>
            Add to calendar
          </a>
        )}
        {row.can_release && (
          <button
            type="button" className="btn btn--light btn--small"
            disabled={busy}
            onClick={() => onRelease(row.pledge_id)}
          >
            I can't make it anymore
          </button>
        )}
      </div>
    </article>
  )
}
