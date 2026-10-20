import { useEffect, useState } from 'react'
import {
  getGrantOptions, grantWish, userMessage,
  type GrantOptions, type GrantResponse, type WishCard as Wish,
} from '../api'
import WishCard from '../components/WishCard'
import { MapLink } from '../components/ItemLink'
import { hours, longDay } from '../dates'

/** The same plain maps search the server builds. No API key. */
function mapsUrl(address: string): string {
  return 'https://www.google.com/maps/search/?api=1&query=' + encodeURIComponent(address)
}

/**
 * The last screen before a wish locks to one donor.
 *
 * Nothing here is a surprise later: what to bring, whether a substitute is
 * fine, what it will cost, and exactly when and where to turn up. The
 * checkbox is not a formality — a donor who cannot make the window should
 * find that out now, while the wish is still on the tree for someone else.
 */
export default function GrantConfirm({
  wish, donorAlias, onGranted, onCancel,
}: {
  wish: Wish
  donorAlias: string
  onGranted: (result: GrantResponse) => void
  onCancel: () => void
}) {
  const [options, setOptions] = useState<GrantOptions | null>(null)
  const [chosen, setChosen] = useState<string>('')
  const [agreed, setAgreed] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getGrantOptions(wish.id, donorAlias)
      .then((result) => {
        setOptions(result)
        setChosen(result.dropoff_choices[0]?.dropoff_date ?? '')
      })
      .catch((e) => setError(userMessage(e, 'We could not open that wish just now.')))
  }, [wish.id, donorAlias])

  if (error) return <p className="form__error">{error}</p>
  if (!options) return <p className="activity__loading">Opening this wish…</p>

  const { what_to_bring: bring, dropoff_choices: choices, hub } = options
  const direct = options.paid_directly_to_provider
  const picked = choices.find((c) => c.dropoff_date === chosen)
  const ready = direct ? agreed : Boolean(picked) && agreed

  async function confirm() {
    setBusy(true)
    setError(null)
    try {
      onGranted(await grantWish(donorAlias, wish.id, direct ? undefined : chosen))
    } catch (e) {
      setError(userMessage(e, 'We could not grant that wish just now. Please try again.'))
      setBusy(false)
    }
  }

  return (
    <div className="confirm">
      <h1 className="page__title">Before you grant this</h1>

      <WishCard wish={options.wish} />

      {bring && (
        <section className="confirm__block">
          <h2 className="confirm__heading">{bring.headline}</h2>
          <p className="confirm__item">{bring.item}</p>
          <dl className="confirm__facts">
            {bring.brand && <div><dt>Brand</dt><dd>{bring.brand}</dd></div>}
            {bring.size && <div><dt>Size</dt><dd>{bring.size}</dd></div>}
            {bring.color && <div><dt>Color</dt><dd>{bring.color}</dd></div>}
            {bring.essentials && <div><dt>What matters</dt><dd>{bring.essentials}</dd></div>}
            <div>
              <dt>Estimated cost</dt>
              <dd>
                ${options.estimated_cost_usd.toFixed(0)}
                {options.cost_is_estimate && <span className="pill-estimate">Estimated</span>}
              </dd>
            </div>
          </dl>
          {bring.link && <p className="confirm__link">{bring.link}</p>}
          <p className={`confirm__sub confirm__sub--${bring.substitute_ok ? 'ok' : 'no'}`}>
            {bring.substitute_note}
          </p>
        </section>
      )}

      {direct && (
        <section className="confirm__block confirm__block--direct">
          <h2 className="confirm__heading">
            ${options.estimated_cost_usd.toFixed(0)} paid to the provider
          </h2>
          <p className="confirm__item">{options.direct_payment_note}</p>
        </section>
      )}

      {!direct && (
        <section className="confirm__block">
          <h2 className="confirm__heading">When and where</h2>
          <p className="confirm__hub">
            <strong>{hub.name}</strong><br />
            <MapLink href={mapsUrl(hub.address)}>{hub.address}</MapLink><br />
            {hub.dropoff_window}
          </p>

          {choices.length > 1 && (
            <fieldset className="fieldset">
              <legend className="field__label">Which drop-off suits you?</legend>
              <div className="checks">
                {choices.map((choice) => (
                  <label key={choice.dropoff_date} className="check">
                    <input
                      type="radio" name="dropoff" value={choice.dropoff_date}
                      checked={chosen === choice.dropoff_date}
                      onChange={() => { setChosen(choice.dropoff_date); setAgreed(false) }}
                    />
                    <span>
                      {choice.label}
                      <span className="check__sub">
                        {' '}— delivered {longDay(choice.delivery_date)}
                        {!choice.arrives_in_time && ' (after the date they asked for)'}
                      </span>
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          )}

          {choices.length === 1 && picked && (
            <p className="confirm__single">
              {picked.label}, delivered {longDay(picked.delivery_date)}.
            </p>
          )}
        </section>
      )}

      {!agreed && (
        <p className="confirm__nudge">
          One last thing before you can grant this: tick the box to say you can
          make it. Until you do, the wish stays on the tree for another neighbor.
        </p>
      )}

      <label className={`confirm__agree${agreed ? '' : ' confirm__agree--waiting'}`}>
        <input
          type="checkbox" checked={agreed}
          onChange={(e) => setAgreed(e.target.checked)}
        />
        <span>
          {direct
            ? `I can cover $${options.estimated_cost_usd.toFixed(0)} for this.`
            : `I can drop this off on ${picked?.label ?? 'the chosen day'} between ${hours(hub.dropoff_window)}.`}
        </span>
      </label>

      {error && <p className="form__error" role="alert">{error}</p>}

      <div className="review__actions">
        <button
          className="btn btn--gold" type="button" onClick={confirm}
          disabled={!ready || busy}
          title={agreed ? undefined : 'Tick the box above first'}
        >
          {busy ? 'Granting…' : "I'll grant this wish"}
        </button>
        <button className="btn btn--light" type="button" onClick={onCancel} disabled={busy}>
          Not this one
        </button>
      </div>
    </div>
  )
}
