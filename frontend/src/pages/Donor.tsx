import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Logo from '../components/Logo'
import {
  CATEGORY_LABELS, OCCASION_LABELS, getWishes, grantWish, requestMatches,
  type Category, type GrantResponse, type Match, type Occasion,
  type RegionInfo, type Usage, type WallFilters, type WishCard as Wish,
  userMessage,
} from '../api'
import Thinking from '../components/Thinking'
import TokenPanel from '../components/TokenPanel'
import WishCard from '../components/WishCard'
import { clearSession, getSession } from '../session'

const EMPTY: WallFilters = { categories: [], occasion: '', requestType: '', maxCost: '' }

export default function Donor() {
  const session = getSession()
  const [filters, setFilters] = useState<WallFilters>(EMPTY)
  const [wishes, setWishes] = useState<Wish[]>([])
  const [region, setRegion] = useState<RegionInfo | null>(null)
  const [matches, setMatches] = useState<Match[] | null>(null)
  const [note, setNote] = useState('')
  const [usage, setUsage] = useState<Usage | null>(null)
  const [granted, setGranted] = useState<GrantResponse | null>(null)
  const [busy, setBusy] = useState<'wall' | 'match' | number | null>('wall')
  const [error, setError] = useState<string | null>(null)

  function loadWall(next: WallFilters) {
    setBusy('wall')
    setError(null)
    getWishes(next)
      .then((wall) => { setWishes(wall.wishes); setRegion(wall.region) })
      .catch((e) => setError(userMessage(e, 'We could not load the wish wall.')))
      .finally(() => setBusy(null))
  }

  useEffect(() => { loadWall(EMPTY) }, [])

  if (!session || session.role !== 'donor') {
    return (
      <main className="page">
        <header className="page__nav"><Logo size={26} /></header>
        <h1 className="page__title">Sign in first</h1>
        <p className="page__blurb">
          <Link to="/donor/signup">Create a donor account</Link> to browse and grant wishes.
        </p>
      </main>
    )
  }

  function update(patch: Partial<WallFilters>) {
    const next = { ...filters, ...patch }
    setFilters(next)
    setMatches(null)
    loadWall(next)
  }

  function toggleCategory(category: Category) {
    update({
      categories: filters.categories.includes(category)
        ? filters.categories.filter((c) => c !== category)
        : [...filters.categories, category],
    })
  }

  async function match() {
    setBusy('match')
    setError(null)
    try {
      const result = await requestMatches(session!.alias, filters)
      setMatches(result.matches)
      setNote(result.note)
      setUsage(result.usage)
    } catch (e) {
      setError(userMessage(e, 'We could not fetch your matches just now. Please try again.'))
    } finally {
      setBusy(null)
    }
  }

  async function grant(wish: Wish) {
    setBusy(wish.id)
    setError(null)
    try {
      setGranted(await grantWish(session!.alias, wish.id))
    } catch (e) {
      setError(userMessage(e, 'We could not grant that wish just now. Please try again.'))
      loadWall(filters)
      setMatches(null)
    } finally {
      setBusy(null)
    }
  }

  if (granted) {
    const { logistics } = granted
    return (
      <main className="page">
        <header className="page__nav"><Logo size={26} /></header>
        <h1 className="page__title">Thank you — that wish is yours</h1>
        <p className="page__blurb">{granted.wish.item_description}</p>

        <section className={`logistics logistics--${logistics.kind}`}>
          <h2 className="logistics__headline">{logistics.headline}</h2>
          {logistics.kind === 'hub_dropoff' ? (
            <dl className="logistics__facts">
              <div><dt>Where</dt><dd>{logistics.hub_name}<br />{logistics.hub_address}</dd></div>
              <div><dt>Drop off on</dt><dd>{logistics.dropoff_date}<br />{logistics.dropoff_window}</dd></div>
              <div><dt>Delivered</dt><dd>{logistics.delivery_date}<br />{logistics.delivery_window}</dd></div>
            </dl>
          ) : (
            <>
              <p className="logistics__detail">{logistics.detail}</p>
              <p className="logistics__detail">Paid on {logistics.delivery_date}.</p>
            </>
          )}
          {!granted.arrives_in_time && (
            <p className="logistics__late">{granted.schedule_note}</p>
          )}
        </section>

        <button
          type="button" className="btn btn--light"
          onClick={() => { setGranted(null); loadWall(filters); setMatches(null) }}
        >
          Back to the wish wall
        </button>
      </main>
    )
  }

  const showing = matches ? matches.map((m) => m.wish) : wishes

  return (
    <main className="page page--wide">
      <header className="page__nav"><Logo size={26} /></header>

      <p className="signed-in">
        Signed in as <strong>{session.alias}</strong> · {session.zip}
        <button
          type="button" className="signed-in__switch"
          onClick={() => { clearSession(); window.location.assign('/') }}
        >
          Switch account
        </button>
      </p>

      <h1 className="page__title">Wishes near you</h1>

      <section className="filters" aria-label="Filter the wish wall">
        <div className="filters__row">
          {(Object.keys(CATEGORY_LABELS) as Category[]).map((category) => (
            <button
              key={category} type="button"
              className={`tag${filters.categories.includes(category) ? ' tag--on' : ''}`}
              onClick={() => toggleCategory(category)}
            >
              {CATEGORY_LABELS[category]}
            </button>
          ))}
        </div>

        <div className="filters__row filters__row--inputs">
          <label className="field field--inline">
            <span className="field__label">Occasion</span>
            <select
              className="field__input" value={filters.occasion}
              onChange={(e) => update({ occasion: e.target.value as Occasion | '' })}
            >
              <option value="">Any</option>
              {(Object.keys(OCCASION_LABELS) as Occasion[]).map((o) => (
                <option key={o} value={o}>{OCCASION_LABELS[o]}</option>
              ))}
            </select>
          </label>

          <label className="field field--inline">
            <span className="field__label">Type</span>
            <select
              className="field__input" value={filters.requestType}
              onChange={(e) => update({ requestType: e.target.value as 'specific' | 'flexible' | '' })}
            >
              <option value="">Any</option>
              <option value="specific">Specific item</option>
              <option value="flexible">Flexible need</option>
            </select>
          </label>

          <label className="field field--inline">
            <span className="field__label">Up to ($)</span>
            <input
              className="field__input" type="number" min="0" step="10"
              value={filters.maxCost} placeholder="any"
              onChange={(e) => update({ maxCost: e.target.value })}
            />
          </label>

          <button
            type="button" className="btn btn--primary"
            onClick={match} disabled={busy === 'match'}
          >
            {busy === 'match' ? 'Matching…' : 'Match me to wishes'}
          </button>

          {matches && (
            <button type="button" className="btn btn--light" onClick={() => setMatches(null)}>
              Show the whole wall
            </button>
          )}
        </div>
      </section>

      {error && <p className="form__error" role="alert">{error}</p>}

      {busy === 'match' && (
        <Thinking label="Looking through the wall for wishes that fit you" />
      )}

      {matches && (
        <div className="matchbar">
          <strong>{matches.length} match{matches.length === 1 ? '' : 'es'}</strong> ranked for you
          {note && <span className="matchbar__note"> — {note}</span>}
        </div>
      )}

      <div className="wall">
        <div className="wall__cards">
          {busy === 'wall' && <p className="wall__empty">Loading wishes…</p>}
          {busy !== 'wall' && showing.length === 0 && (
            <div className="wall__empty">
              <p className="wall__empty-title">Nothing here right now</p>
              <p>
                {matches
                  ? 'Nothing on the wall fits those filters today. Try widening them, or browse the whole wall.'
                  : 'No open wishes match those filters today. Try removing a filter — new wishes go up every week.'}
              </p>
            </div>
          )}
          {showing.map((wish) => (
            <WishCard
              key={wish.id}
              wish={wish}
              reason={matches?.find((m) => m.request_id === wish.id)?.reason}
              onGrant={grant}
              granting={busy === wish.id}
            />
          ))}
        </div>

        <div className="wall__side">
          {matches && <TokenPanel usage={usage} />}
          {region && (
            <aside className="hubcard">
              <h2 className="hubcard__title">How it arrives</h2>
              <p>Drop off at <strong>{region.hub_name}</strong>, {region.hub_address}.</p>
              <p>Drop-off: {region.dropoff_window}</p>
              <p>Delivery: {region.delivery_window}</p>
              <p className="hubcard__note">
                Rent and utility wishes are paid straight to the landlord or provider —
                never cash to a family.
              </p>
            </aside>
          )}
        </div>
      </div>
    </main>
  )
}
