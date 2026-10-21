import { useCallback, useEffect, useState } from 'react'
import { getRunSheet, setPledgeStatus, type RunSheet as Sheet,
  userMessage,
} from '../api'
import { SkeletonRows } from '../components/Skeleton'
import ResetPassword from '../components/ResetPassword'

/**
 * One week of logistics. The only screen in Wishing Tree that shows a family's
 * address and phone number, which is why it sits behind the coordinator token.
 */
export default function RunSheet({ token }: { token: string }) {
  const [weekOf, setWeekOf] = useState<string | undefined>(undefined)
  const [sheet, setSheet] = useState<Sheet | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(() => {
    getRunSheet(token, weekOf).then(setSheet).catch((e) => setError(userMessage(e, 'We could not load the run sheet.')))
  }, [token, weekOf])

  useEffect(() => { load() }, [load])

  async function mark(pledgeIds: number[], status: string) {
    setBusy(true)
    setNote('')
    try {
      const result = await setPledgeStatus(token, pledgeIds, status)
      if (result.note) setNote(result.note)
      load()
    } catch (e) {
      setError(userMessage(e, 'We could not update that just now. Please try again.'))
    } finally {
      setBusy(false)
    }
  }

  if (error) return <p className="form__error">{error}</p>
  if (!sheet) {
    return (
      <>
        <p className="sr-only" role="status">Loading the run sheet…</p>
        <SkeletonRows count={3} />
      </>
    )
  }

  return (
    <section className="sheet">
      <header className="sheet__head">
        <button type="button" className="btn btn--light" onClick={() => setWeekOf(sheet.previous_week)}>
          ← Previous week
        </button>
        <div className="sheet__week">
          <strong>{sheet.week_start} → {sheet.week_end}</strong>
          {sheet.is_this_week && <span className="chip">This week</span>}
        </div>
        <button type="button" className="btn btn--light" onClick={() => setWeekOf(sheet.next_week)}>
          Next week →
        </button>
      </header>

      <p className="sheet__hub">
        {sheet.hub.name}, {sheet.hub.address} · Drop-off {sheet.hub.dropoff_window} ·
        Delivery {sheet.hub.delivery_window}
      </p>

      {note && <p className="sheet__note">{note}</p>}

      <h3 className="sheet__section">
        Drop-offs <span className="sheet__count">{sheet.counts.dropoffs}</span>
      </h3>
      {sheet.dropoffs.length === 0 && <p className="sheet__empty">Nothing expected this week.</p>}
      {sheet.dropoffs.map((row) => (
        <div key={row.pledge_id} className={`row row--${row.status.replace(' ', '-')}`}>
          <div className="row__main">
            <p className="row__who">{row.donor_alias}</p>
            <p className="row__contact">{row.donor_address} · {row.donor_phone}</p>
            <p className="row__item">{row.item}</p>
            <ResetPassword token={token} alias={row.donor_alias} />
          </div>
          <div className="row__side">
            <span className={`status status--${row.status.replace(' ', '-')}`}>{row.status}</span>
            <span className="row__date">{row.dropoff_date}</span>
            {row.status === 'scheduled' && (
              <div className="row__buttons">
                <button type="button" className="btn btn--primary btn--small" disabled={busy}
                        onClick={() => mark([row.pledge_id], 'dropped_off')}>
                  Dropped off
                </button>
                <button type="button" className="btn btn--light btn--small" disabled={busy}
                        onClick={() => mark([row.pledge_id], 'missed')}>
                  Missed
                </button>
              </div>
            )}
          </div>
        </div>
      ))}

      <h3 className="sheet__section">
        Deliveries <span className="sheet__count">{sheet.counts.deliveries}</span>
        {sheet.counts.needs_reschedule > 0 && (
          <span className="chip chip--flag">{sheet.counts.needs_reschedule} to reschedule</span>
        )}
      </h3>
      {sheet.deliveries.length === 0 && <p className="sheet__empty">Nothing going out this week.</p>}
      {sheet.deliveries.map((row) => (
        <div key={`${row.family_alias}-${row.delivery_date}`} className={`row row--${row.status}`}>
          <div className="row__main">
            <p className="row__who">{row.family_alias}</p>
            <p className="row__contact">{row.family_address} · {row.family_phone}</p>
            <ResetPassword token={token} alias={row.family_alias} />
            <ul className="row__items">
              {row.items.map((item, i) => <li key={i}>{item}</li>)}
            </ul>
          </div>
          <div className="row__side">
            <span className={`status status--${row.status}`}>{row.status}</span>
            <span className="row__date">{row.delivery_date}</span>
            {row.window_responses.includes('needs_reschedule') ? (
              <span className="status status--missed">needs reschedule</span>
            ) : (
              <span className={`status status--${row.confirmed ? 'confirmed' : 'waiting'}`}>
                {row.confirmed ? 'confirmed' : 'not confirmed'}
              </span>
            )}
            {row.status === 'scheduled' && (
              <div className="row__buttons">
                <button type="button" className="btn btn--primary btn--small" disabled={busy}
                        onClick={() => mark(row.pledge_ids, 'delivered')}>
                  Delivered
                </button>
              </div>
            )}
          </div>
        </div>
      ))}

      <h3 className="sheet__section">
        Rent &amp; utilities <span className="sheet__count">{sheet.counts.direct_payments}</span>
      </h3>
      {sheet.direct_payments.length === 0 && <p className="sheet__empty">None this week.</p>}
      {sheet.direct_payments.map((row) => (
        <div key={row.pledge_id} className="row row--direct">
          <div className="row__main">
            <p className="row__who">{row.family_alias} · funded by {row.donor_alias}</p>
            <p className="row__item">{row.item}</p>
            <p className="row__contact">{row.note}</p>
          </div>
          <div className="row__side">
            <span className="status status--direct">${row.amount_usd.toFixed(0)}</span>
            <span className="row__date">pay by {row.pay_by}</span>
            {row.status !== 'delivered' && (
              <div className="row__buttons">
                <button type="button" className="btn btn--primary btn--small" disabled={busy}
                        onClick={() => mark([row.pledge_id], 'delivered')}>
                  Paid
                </button>
              </div>
            )}
          </div>
        </div>
      ))}
    </section>
  )
}
